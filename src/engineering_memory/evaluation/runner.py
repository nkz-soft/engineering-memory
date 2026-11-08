"""Evaluate recall through the same read-only stdio MCP surface as consumers."""

import logging
import os
import sys
from contextlib import contextmanager
from contextvars import ContextVar

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult

from engineering_memory.evaluation.benchmark import (
    Benchmark,
    EvaluationModel,
    RecallMatch,
    score_question,
)
from engineering_memory.evaluation.reports import RunProfile, RunReport
from engineering_memory.settings import access_subprocess_environment

_CALL_TIMEOUT = 30
_PRIVATE_RECALL = ContextVar("private_recall", default=False)


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
        return not _PRIVATE_RECALL.get()

    token = _PRIVATE_RECALL.set(True)
    for logger in loggers:
        logger.addFilter(guard)
    try:
        yield
    finally:
        for logger in loggers:
            logger.removeFilter(guard)
        _PRIVATE_RECALL.reset(token)


def _server_parameters() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-c", "from engineering_memory.cli import main; main()", "serve"],
        env=access_subprocess_environment(),
    )


async def run_recall(benchmark: Benchmark, profile: RunProfile) -> RunReport:
    outcomes = []
    scope = anyio.CancelScope()

    async def on_message(message):
        # The SDK normally reports transport errors to the callback and keeps reading.
        if isinstance(message, Exception):
            scope.cancel()

    try:
        with scope, _quiet_transport(), open(os.devnull, "w", encoding="utf-8") as discarded:
            async with (
                stdio_client(_server_parameters(), errlog=discarded) as (reader, writer),
                ClientSession(
                    reader, writer, read_timeout_seconds=_CALL_TIMEOUT, message_handler=on_message
                ) as session,
            ):
                with anyio.fail_after(_CALL_TIMEOUT):
                    await session.initialize()
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
