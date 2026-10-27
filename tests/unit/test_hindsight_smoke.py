"""Synthetic probe tests; MockTransport never opens a network connection."""

import asyncio
import importlib
import json
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr
from typer.testing import CliRunner

from engineering_memory.settings import HindsightSettings, LlmSettings, Settings, SettingsError

CANARY = "synthetic-private-canary"
BANK = "/v1/default/banks/{bank_id}"
RETAIN = BANK + "/memories"
RECALL = RETAIN + "/recall"
OPERATION = BANK + "/operations/{operation_id}"


def module():
    return importlib.import_module("engineering_memory.memory.hindsight.smoke")


def settings(url="http://engine.invalid:8888/"):
    return Settings(
        hindsight=HindsightSettings(base_url=url, token=SecretStr("synthetic-engine-token")),
        llm=LlmSettings(base_url="http://proxy.invalid:4000/v1", api_key=SecretStr(CANARY)),
    )


class Engine:
    def __init__(self, stage=None, status=500, body=None, queued=False):
        self.requests = []
        self.content = ""
        self.stage, self.status, self.body, self.queued = stage, status, body, queued
        self.operations = iter(["processing", "completed"])

    def __call__(self, request):
        self.requests.append(request)
        path = request.url.path
        stage = (
            "cleanup"
            if request.method == "DELETE"
            else "readiness"
            if path.endswith("/health/ready")
            else "schema"
            if path.endswith("/openapi.json")
            else "retain"
            if path.endswith("/memories")
            else "recall"
            if path.endswith("/recall")
            else "completion"
        )
        if stage == self.stage:
            return httpx.Response(
                self.status, json=self.body if self.body is not None else {"detail": CANARY}
            )
        if stage == "schema":
            return httpx.Response(
                200,
                json={
                    "paths": {
                        "/health/ready": {"get": {}},
                        RETAIN: {"post": {}},
                        RECALL: {"post": {}},
                        BANK: {"delete": {}},
                        OPERATION: {"get": {}},
                    }
                },
            )
        if stage == "retain":
            self.content = json.loads(request.content)["items"][0]["content"]
            result = {
                "success": True,
                "bank_id": path.split("/")[-2],
                "items_count": 1,
                "async": self.queued,
            }
            if self.queued:
                result["operation_id"] = "12345678-1234-1234-1234-123456789abc"
            return httpx.Response(200, json=result)
        if stage == "completion":
            return httpx.Response(200, json={"status": next(self.operations)})
        if stage == "recall":
            return httpx.Response(
                200,
                json={"results": [{"text": self.content}]},
            )
        return httpx.Response(200, json={"success": True})


def run(engine, **kwargs):
    return module().run_smoke(settings(), transport=httpx.MockTransport(engine), **kwargs)


def test_retains_recalls_and_cleans_only_generated_unique_banks():
    engine = Engine()
    first, second = run(engine), run(engine)
    assert first.bank_id != second.bank_id
    for result in (first, second):
        UUID(result.run_id)
        assert result.bank_id == f"engineering-memory-smoke-{result.run_id}"
    writes = [r for r in engine.requests if r.method == "POST" and r.url.path.endswith("/memories")]
    assert len(writes) == 2
    body = json.loads(writes[0].content)
    assert body["async"] is False
    assert "cobalt-orchard" in body["items"][0]["content"]
    assert "Orchard Observatory" in body["items"][0]["content"]
    assert body["items"][0]["timestamp"] == "2026-01-01T00:00:00Z"
    assert body["items"][0]["document_id"] == f"smoke:{first.run_id}"
    assert [r.url.path for r in engine.requests if r.method == "DELETE"] == [
        BANK.format(bank_id=r.bank_id) for r in (first, second)
    ]
    assert all("engineering-global" not in str(r.url) for r in engine.requests)
    assert all(
        r.headers["authorization"] == "Bearer synthetic-engine-token" for r in engine.requests
    )
    assert all(
        CANARY not in str(r.url) + str(r.headers) + r.content.decode() for r in engine.requests
    )


def test_keep_scratch_does_not_delete():
    engine = Engine()
    assert run(engine, keep_scratch=True).kept
    assert not any(r.method == "DELETE" for r in engine.requests)


@pytest.mark.parametrize("stage", ["readiness", "schema", "retain", "recall", "cleanup"])
@pytest.mark.parametrize("status", [401, 500])
def test_http_failure_is_safe_and_stage_specific(stage, status):
    smoke, engine = module(), Engine(stage, status)
    with pytest.raises(smoke.SmokeError) as caught:
        run(engine)
    assert stage in str(caught.value)
    assert CANARY not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    if stage in {"readiness", "schema"}:
        assert not any(r.method in {"POST", "DELETE"} for r in engine.requests)


@pytest.mark.parametrize(
    "body",
    [
        {"results": []},
        {"results": [{"text": "wrong"}]},
        [],
        {"results": "bad"},
        {"results": [None]},
    ],
)
def test_wrong_or_malformed_recall_fails_and_cleans(body):
    smoke, engine = module(), Engine("recall", 200, body)
    with pytest.raises(smoke.SmokeError):
        run(engine)
    assert engine.requests[-1].method == "DELETE"


def test_invalid_json_is_safe():
    smoke, engine = module(), Engine()

    def malformed(request):
        return (
            httpx.Response(200, content=CANARY)
            if request.url.path.endswith("/recall")
            else engine(request)
        )

    with pytest.raises(smoke.SmokeError) as caught:
        run(malformed)
    assert CANARY not in str(caught.value) and caught.value.__context__ is None
    assert engine.requests[-1].method == "DELETE"


def test_queued_retain_completes_before_recall():
    engine = Engine(queued=True)
    run(engine)
    assert sum("/operations/" in r.url.path for r in engine.requests) == 2
    assert engine.requests[-2].url.path.endswith("/recall")


@pytest.mark.parametrize("state", ["failed", "cancelled", "not_found", "unknown"])
def test_bad_operation_never_counts_as_completed(state):
    smoke, engine = (
        module(),
        Engine("completion", 200, {"status": state, "error_message": CANARY}, True),
    )
    with pytest.raises(smoke.SmokeError) as caught:
        run(engine)
    assert CANARY not in str(caught.value)
    assert not any(r.url.path.endswith("/recall") for r in engine.requests)


def test_pending_operation_hits_overall_deadline():
    smoke, engine = module(), Engine("completion", 200, {"status": "pending"}, True)
    with pytest.raises(smoke.SmokeError, match="deadline"):
        run(engine, timeout=0.05)
    assert not any(r.url.path.endswith("/recall") for r in engine.requests)


def test_slow_request_has_overall_deadline_and_reserved_cleanup_budget():
    smoke, engine = module(), Engine()

    async def delayed(request):
        if request.url.path.endswith("/memories"):
            await asyncio.sleep(1)
        return engine(request)

    with pytest.raises(smoke.SmokeError, match="deadline"):
        run(delayed, timeout=0.5)
    assert engine.requests[-1].method == "DELETE"


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_timeout_is_positive_finite_before_network(timeout):
    smoke, engine = module(), Engine()
    with pytest.raises(smoke.SmokeError):
        run(engine, timeout=timeout)
    assert not engine.requests


@pytest.mark.parametrize(
    "url",
    [
        "http://user:password@engine.invalid/",
        "http://engine.invalid/?token=private",
        "http://engine.invalid/#private",
    ],
)
def test_unsafe_url_is_rejected_without_disclosing_it(url):
    smoke, engine = module(), Engine()
    with pytest.raises(smoke.SmokeError) as caught:
        smoke.run_smoke(settings(url), transport=httpx.MockTransport(engine))
    assert "password" not in str(caught.value) and "private" not in str(caught.value)
    assert not engine.requests


def test_schema_mismatch_stops_before_write():
    smoke, engine = module(), Engine("schema", 200, {"paths": {}})
    with pytest.raises(smoke.SmokeError, match="schema"):
        run(engine)
    assert not any(r.method == "POST" for r in engine.requests)


def test_retain_rejection_is_not_retried_or_recalled():
    smoke, engine = module(), Engine("retain", 200, {"success": False, "async": False})
    with pytest.raises(smoke.SmokeError):
        run(engine)
    assert sum(r.method == "POST" for r in engine.requests) == 1


def test_cleanup_failure_preserves_primary_error():
    smoke, engine = module(), Engine("retain", 500)

    def fail_both(request):
        return (
            httpx.Response(500, json={"detail": CANARY})
            if request.method == "DELETE"
            else engine(request)
        )

    with pytest.raises(smoke.SmokeError) as caught:
        run(fail_both)
    assert "retain" in str(caught.value) and "cleanup" in str(caught.value)
    assert CANARY not in str(caught.value)


def test_help_is_offline_and_does_not_allow_arbitrary_content_or_bank():
    result = CliRunner().invoke(module().app, ["--help"])
    assert result.exit_code == 0 and "--keep-scratch" in result.output
    assert all(flag not in result.output for flag in ("--bank-id", "--content", "--input-file"))


def test_cli_configuration_failure_is_safe(monkeypatch):
    smoke = module()

    def fail():
        raise SettingsError(CANARY)

    monkeypatch.setattr(smoke, "load_settings", fail)
    result = CliRunner().invoke(smoke.app, [])
    assert result.exit_code == 1 and "configuration" in result.output
    assert CANARY not in result.output


@pytest.mark.parametrize("token", ["synthetic-雪", "synthetic\r\nInjected: value"])
def test_invalid_engine_token_fails_safely_before_transport(token):
    smoke, engine = module(), Engine()
    configured = settings()
    configured = configured.model_copy(
        update={"hindsight": configured.hindsight.model_copy(update={"token": SecretStr(token)})}
    )
    with pytest.raises(smoke.SmokeError) as caught:
        smoke.run_smoke(configured, transport=httpx.MockTransport(engine))
    assert token not in str(caught.value) and not engine.requests


def test_transport_error_never_leaks_url_or_details():
    smoke = module()

    def fail(request):
        raise httpx.ConnectError(CANARY, request=request)

    with pytest.raises(smoke.SmokeError) as caught:
        run(fail)
    assert CANARY not in str(caught.value)
    assert caught.value.__context__ is None


def test_redirect_is_not_followed_with_engine_token():
    smoke, engine = module(), Engine("readiness", 302, {"detail": CANARY})
    with pytest.raises(smoke.SmokeError):
        run(engine)
    assert len(engine.requests) == 1


def test_cli_success_reports_http_only_and_proxy_unverified(monkeypatch):
    smoke = module()
    engine = Engine()
    monkeypatch.setattr(smoke, "load_settings", settings)
    actual = smoke.run_smoke
    monkeypatch.setattr(
        smoke,
        "run_smoke",
        lambda configured, **kwargs: actual(
            configured,
            transport=httpx.MockTransport(engine),
            **kwargs,
        ),
    )
    result = CliRunner().invoke(smoke.app, [])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["http_smoke"] == "passed"
    assert "unverified" in payload["proxy_observation"]
    assert CANARY not in result.output


def test_fact_from_an_older_smoke_run_cannot_pass_a_new_run():
    smoke, engine = (
        module(),
        Engine("recall", 200, {"results": [{"text": "The project codename is cobalt-orchard."}]}),
    )
    with pytest.raises(smoke.SmokeError, match="recall"):
        run(engine)


@pytest.mark.parametrize("fails", [False, True])
def test_transport_shutdown_is_bounded_and_safe(fails):
    smoke, engine = module(), Engine()

    class ClosingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return engine(request)

        async def aclose(self):
            if fails:
                raise httpx.RequestError(CANARY)
            await asyncio.sleep(1)

    with pytest.raises(smoke.SmokeError, match="shutdown") as caught:
        smoke.run_smoke(settings(), timeout=0.1, transport=ClosingTransport())
    assert CANARY not in str(caught.value)
    assert caught.value.result.bank_id.startswith("engineering-memory-smoke-")
