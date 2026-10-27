"""Synthetic-only development probe; not an importer or a consumer write tool.

Run explicitly with ``python -m engineering_memory.memory.hindsight.smoke``.
Engine success and proxy-side routing observation are separate evidence.
"""

import asyncio
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

import httpx
import typer

from engineering_memory.settings import Settings, SettingsError, load_settings

_PREFIX = "engineering-memory-smoke-"
_BANK = "/v1/default/banks/{bank_id}"
_RETAIN = _BANK + "/memories"
_RECALL = _RETAIN + "/recall"
_OPERATION = _BANK + "/operations/{operation_id}"
_EXPECTED = "cobalt-orchard"
_REQUIRED = {_RETAIN: "post", _RECALL: "post", _BANK: "delete", _OPERATION: "get"}

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)


@dataclass(frozen=True)
class SmokeResult:
    run_id: str
    bank_id: str
    started_at: str
    finished_at: str
    kept: bool
    proxy_observation: str = "unverified; confirm separately at the proxy"


class SmokeError(RuntimeError):
    """Only fixed safe diagnostics and generated run metadata cross this boundary."""

    def __init__(self, message: str, result: SmokeResult | None = None) -> None:
        super().__init__(message)
        self.result = result


class _ProbeFailure(Exception):
    """Internal control flow; never exposes an upstream response or exception."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def _execute(
    settings: Settings,
    timeout: float,
    keep_scratch: bool,
    transport: httpx.AsyncBaseTransport | None,
) -> tuple[SmokeResult, str | None]:
    run_id = str(uuid4())
    bank_id = f"{_PREFIX}{run_id}"
    expected_fact = f"{_EXPECTED}-{UUID(run_id).hex[:12]}"
    started = _now()
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    work_deadline = deadline - min(5.0, timeout * 0.1)
    stage = "readiness"
    attempted = False
    problem = None
    headers = {}
    if settings.hindsight.token is not None:
        headers["Authorization"] = f"Bearer {settings.hindsight.token.get_secret_value()}"
    base = str(settings.hindsight.base_url).rstrip("/")
    client = httpx.AsyncClient(
        base_url=base + "/",
        headers=headers,
        transport=transport,
        trust_env=False,
        follow_redirects=False,
    )

    async def request(method: str, path: str, *, cleanup: bool = False, **kwargs: Any):
        remaining = (deadline if cleanup else work_deadline) - loop.time()
        if remaining <= 0:
            raise _ProbeFailure(f"{stage}: deadline exceeded")
        response = await client.request(method, base + path, timeout=remaining, **kwargs)
        if cleanup and response.status_code == 404:
            return None
        if not 200 <= response.status_code < 300:
            raise _ProbeFailure(f"{stage}: HTTP {response.status_code}")
        return response

    try:
        async with asyncio.timeout_at(work_deadline):
            await request("GET", "/health/ready")
            stage = "schema"
            response = await request("GET", "/openapi.json")
            schema = response.json()
            paths = schema.get("paths") if isinstance(schema, dict) else None
            if not isinstance(paths, dict) or any(
                not isinstance(paths.get(path), dict) or method not in paths[path]
                for path, method in _REQUIRED.items()
            ):
                raise _ProbeFailure("schema: required pinned API routes are unavailable")
            stage = "retain"
            attempted = True
            response = await request(
                "POST",
                _RETAIN.format(bank_id=bank_id),
                json={
                    "items": [
                        {
                            "content": (
                                "The synthetic Orchard Observatory chose "
                                f"{expected_fact} as its codename."
                            ),
                            "document_id": f"smoke:{run_id}",
                            "timestamp": "2026-01-01T00:00:00Z",
                        }
                    ],
                    "async": False,
                },
            )
            retained = response.json()
            if (
                not isinstance(retained, dict)
                or retained.get("success") is not True
                or retained.get("bank_id") != bank_id
                or retained.get("items_count") != 1
                or not isinstance(retained.get("async"), bool)
            ):
                raise _ProbeFailure("retain: response did not confirm the scratch write")
            if retained["async"]:
                stage = "completion"
                operation_id = str(UUID(retained.get("operation_id", "")))
                if retained.get("operation_ids") not in (None, [operation_id]):
                    raise _ProbeFailure("completion: unexpected operation group")
                while True:
                    response = await request(
                        "GET",
                        _OPERATION.format(
                            bank_id=bank_id,
                            operation_id=operation_id,
                        ),
                    )
                    operation = response.json()
                    status = operation.get("status") if isinstance(operation, dict) else None
                    if status == "completed":
                        break
                    if status not in {"pending", "processing"}:
                        raise _ProbeFailure("completion: operation did not complete successfully")
                    await asyncio.sleep(0.25)
            stage = "recall"
            response = await request(
                "POST",
                _RECALL.format(bank_id=bank_id),
                json={
                    "query": "What codename did the synthetic Orchard Observatory choose?",
                    "types": ["world", "experience"],
                    "budget": "low",
                },
            )
            recalled = response.json()
            results = recalled.get("results") if isinstance(recalled, dict) else None
            if not isinstance(results, list) or not any(
                isinstance(item, dict)
                and isinstance(item.get("text"), str)
                and expected_fact in item["text"].casefold()
                for item in results
            ):
                raise _ProbeFailure("recall: expected synthetic fact was not found")
    except _ProbeFailure as exc:
        problem = str(exc)
    except TimeoutError:
        problem = f"{stage}: deadline exceeded"
    except httpx.HTTPError:
        problem = f"{stage}: network request failed"
    except (ValueError, TypeError, AttributeError):
        problem = f"{stage}: invalid response"

    if attempted and not keep_scratch:
        stage = "cleanup"
        try:
            # No caller-supplied identity is accepted; validate our generated target too.
            if bank_id != f"{_PREFIX}{UUID(run_id)}":
                raise _ProbeFailure("cleanup: scratch identity is invalid")
            async with asyncio.timeout_at(deadline):
                response = await request("DELETE", _BANK.format(bank_id=bank_id), cleanup=True)
                if response is not None and response.status_code != 204:
                    deleted = response.json()
                    if not isinstance(deleted, dict) or deleted.get("success") is not True:
                        raise _ProbeFailure("cleanup: deletion was not confirmed")
        except _ProbeFailure as exc:
            problem = f"{problem}; {exc}" if problem else str(exc)
        except (httpx.HTTPError, TimeoutError, ValueError, TypeError):
            cleanup_problem = "cleanup: request failed or deadline exceeded"
            problem = f"{problem}; {cleanup_problem}" if problem else cleanup_problem
    try:
        async with asyncio.timeout_at(deadline):
            await client.aclose()
    except Exception:
        # A backend close can fail too; never render its potentially private diagnostics.
        shutdown_problem = "shutdown: request failed or deadline exceeded"
        problem = f"{problem}; {shutdown_problem}" if problem else shutdown_problem
    return SmokeResult(run_id, bank_id, started, _now(), keep_scratch), problem


def run_smoke(
    settings: Settings,
    *,
    timeout: float = 180.0,
    keep_scratch: bool = False,
    transport: httpx.AsyncBaseTransport | None = None,
) -> SmokeResult:
    """Probe only generated content; an injected transport enables offline verification."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise SmokeError("configuration: timeout must be positive and finite")
    if settings.hindsight.token is not None:
        token = settings.hindsight.token.get_secret_value()
        if not token or any(not 32 <= ord(char) <= 126 for char in token):
            raise SmokeError("configuration: engine token must be a valid ASCII header value")
    url = httpx.URL(str(settings.hindsight.base_url))
    if url.userinfo or url.query or url.fragment:
        raise SmokeError(
            "configuration: engine URL must not contain credentials, query or fragment"
        )
    result, problem = asyncio.run(_execute(settings, timeout, keep_scratch, transport))
    # Raise only after all response/transport handlers have exited: no unsafe exception chain.
    if problem:
        raise SmokeError(problem, result)
    return result


@app.command()
def main(
    timeout: Annotated[
        float, typer.Option(help="Overall deadline in seconds, including cleanup.")
    ] = 180,
    keep_scratch: Annotated[
        bool, typer.Option(help="Keep this run's synthetic bank for inspection.")
    ] = False,
) -> None:
    """Write and recall one synthetic fact; confirm proxy routing separately."""
    problem = None
    result = None
    try:
        result = run_smoke(load_settings(), timeout=timeout, keep_scratch=keep_scratch)
    except SettingsError:
        problem = "configuration: could not load settings; check the documented variable names"
    except SmokeError as exc:
        problem, result = str(exc), exc.result
    if problem:
        output = asdict(result) if result else {}
        typer.echo(json.dumps({**output, "http_smoke": "failed", "error": problem}), err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps({**asdict(result), "http_smoke": "passed"}))


if __name__ == "__main__":
    app()
