"""Evaluate recall and reflection through the same read-only stdio MCP surface as consumers."""

import logging
import os
import sys
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from time import perf_counter

import anyio
from mcp import ClientSession, MCPError
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CONNECTION_CLOSED, REQUEST_TIMEOUT, CallToolResult

from engineering_memory.evaluation.benchmark import (
    RECALL_LIMIT,
    Benchmark,
    EvaluationModel,
    RecallMatch,
    score_question,
)
from engineering_memory.evaluation.reflect import (
    Failure,
    Operation,
    OperationOutcome,
    PairedResult,
    ReflectCase,
    ReflectCaseSet,
    ReflectResponse,
    ReflectRun,
    SearchResponse,
)
from engineering_memory.evaluation.reports import RunProfile, RunReport
from engineering_memory.settings import access_subprocess_environment

_CALL_TIMEOUT = 30
_PRIVATE_EVALUATION = ContextVar("private_evaluation", default=False)


class RecallFailed(RuntimeError):
    """The consumer surface did not return valid results."""


class _SearchResponse(EvaluationModel):
    results: list[RecallMatch]


@contextmanager
def _quiet_transport():
    # SDK diagnostics can include an invalid wire payload. Leave other sessions' logs alone.
    names = (
        "mcp.client.stdio",
        "client",  # ClientSession's logger in MCP 2.3.
        "mcp.shared.jsonrpc_dispatcher",
        "mcp.os.win32.utilities",
    )
    loggers = [logging.getLogger(name) for name in names]

    def guard(_):
        return not _PRIVATE_EVALUATION.get()

    token = _PRIVATE_EVALUATION.set(True)
    for logger in loggers:
        logger.addFilter(guard)
    try:
        yield
    finally:
        for logger in loggers:
            logger.removeFilter(guard)
        _PRIVATE_EVALUATION.reset(token)


def _server_parameters() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-c", "from engineering_memory.cli import main; main()", "serve"],
        env=access_subprocess_environment(),
    )


@asynccontextmanager
async def _evaluation_session(scope: anyio.CancelScope):
    async def on_message(message):
        # The SDK reports malformed transport messages to the callback and keeps reading.
        if isinstance(message, Exception):
            scope.cancel()

    with _quiet_transport(), open(os.devnull, "w", encoding="utf-8") as discarded:
        async with (
            stdio_client(_server_parameters(), errlog=discarded) as (reader, writer),
            ClientSession(
                reader, writer, read_timeout_seconds=_CALL_TIMEOUT, message_handler=on_message
            ) as session,
        ):
            with anyio.fail_after(_CALL_TIMEOUT):
                await session.initialize()
            yield session


async def run_recall(benchmark: Benchmark, profile: RunProfile) -> RunReport:
    outcomes = []
    scope = anyio.CancelScope()
    try:
        with scope:
            async with _evaluation_session(scope) as session:
                for question in benchmark.questions:
                    with anyio.fail_after(_CALL_TIMEOUT):
                        response = await session.call_tool(
                            "search_memory",
                            {
                                "query": question.query,
                                "tags": [benchmark.project_tag],
                                "limit": benchmark.limit,
                            },
                        )
                    if not isinstance(response, CallToolResult) or response.is_error:
                        raise RecallFailed("recall failed")
                    data = _SearchResponse.model_validate(response.structured_content)
                    outcomes.append(score_question(question, data.results))
    except Exception:
        raise RecallFailed("recall failed") from None
    if scope.cancel_called:
        raise RecallFailed("recall failed")
    return RunReport.from_outcomes(benchmark, profile, outcomes)


def _failed(operation: Operation, elapsed_ms: float, failure: Failure) -> OperationOutcome:
    return OperationOutcome(
        operation=operation, status="failed", elapsed_ms=elapsed_ms, failure=failure
    )


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1_000, 3)


def _evaluate_response(
    operation: Operation, case: ReflectCase, response: CallToolResult, elapsed_ms: float
) -> OperationOutcome:
    if not isinstance(response, CallToolResult):
        return _failed(operation, elapsed_ms, "invalid_response")
    if response.is_error:
        return _failed(operation, elapsed_ms, "tool_error")
    try:
        if operation == "search_memory":
            search = SearchResponse.model_validate(response.structured_content)
            if any(match.provenance.project != case.project for match in search.results):
                raise ValueError("unexpected project")
            return OperationOutcome(
                operation=operation,
                status="completed" if search.results else "insufficient_evidence",
                elapsed_ms=elapsed_ms,
                results=search.results,
            )
        reflection = ReflectResponse.model_validate(response.structured_content)
        if any(ref.provenance.project != case.project for ref in reflection.references):
            raise ValueError("unexpected project")
        return OperationOutcome(
            operation=operation,
            status=reflection.status,
            elapsed_ms=elapsed_ms,
            answer=reflection.answer,
            references=reflection.references,
        )
    except ValueError:
        return _failed(operation, elapsed_ms, "invalid_response")


async def _evaluate_call(
    session: ClientSession, operation: Operation, case: ReflectCase, started: float
) -> OperationOutcome:
    arguments = (
        {"query": case.question, "tags": [f"project:{case.project}"], "limit": RECALL_LIMIT}
        if operation == "search_memory"
        else {"query": case.question, "project": case.project}
    )
    try:
        with anyio.fail_after(_CALL_TIMEOUT):
            response = await session.call_tool(operation, arguments)
    except TimeoutError:
        return _failed(operation, _elapsed_ms(started), "timeout")
    except MCPError as error:
        if error.code == CONNECTION_CLOSED:
            raise
        category = "timeout" if error.code == REQUEST_TIMEOUT else "tool_error"
        return _failed(operation, _elapsed_ms(started), category)
    return _evaluate_response(operation, case, response, _elapsed_ms(started))


async def run_reflect(case_set: ReflectCaseSet) -> ReflectRun:
    """Measure both operations through one consumer session on the configured bank."""
    started_at = datetime.now(UTC)
    pairs = [
        PairedResult(
            case_id=case.id,
            kind=case.kind,
            search_memory=OperationOutcome(operation="search_memory", status="unattempted"),
            reflect=OperationOutcome(operation="reflect", status="unattempted"),
        )
        for case in case_set.cases
    ]
    scope = anyio.CancelScope()
    transport_failed = False
    try:
        with scope:
            async with _evaluation_session(scope) as session:
                # Warm the SDK's tool-schema cache before timing either operation.
                with anyio.fail_after(_CALL_TIMEOUT):
                    await session.list_tools()
                for case, pair in zip(case_set.cases, pairs, strict=True):
                    for operation in ("search_memory", "reflect"):
                        started = perf_counter()
                        try:
                            outcome = await _evaluate_call(session, operation, case, started)
                        except (Exception, anyio.get_cancelled_exc_class()):
                            setattr(
                                pair,
                                operation,
                                _failed(operation, _elapsed_ms(started), "transport"),
                            )
                            raise
                        setattr(pair, operation, outcome)
    except Exception:
        transport_failed = True
    transport_failed = transport_failed or scope.cancel_called
    return ReflectRun(
        case_set_version=case_set.version,
        started_at=started_at,
        profile=case_set.profile,
        status="incomplete" if transport_failed else "complete",
        failure="transport" if transport_failed else None,
        pairs=pairs,
    )
