import json
from pathlib import Path

import httpx
import pytest

from engineering_memory.memory.hindsight.provision import (
    ProvisionError,
    mission_text,
    provision,
)
from engineering_memory.settings import HindsightSettings


def settings(url="http://engine", bank="scratch"):
    return HindsightSettings(base_url=url, bank_id=bank, token="synthetic-canary")


def test_canonical_mission():
    architecture = Path("ARCHITECTURE.md").read_text(encoding="utf-8")
    expected = (
        architecture.split("## 12. Retain mission", 1)[1].split("```text\n")[1].split("```")[0]
    )
    assert mission_text() == expected


def test_repeat_replaces_only_mission_and_verifies():
    state = {"retain_mission": "older", "reflect_mission": "preserve"}
    calls = []

    async def handle(request):
        calls.append(request.method)
        assert request.headers["Authorization"] == "Bearer synthetic-canary"
        assert request.url.path == "/v1/default/banks/scratch/config"
        if request.method == "PATCH":
            body = json.loads(request.content)
            assert body == {"updates": {"retain_mission": mission_text()}}
            state.update(body["updates"])
        return httpx.Response(200, json={"config": state})

    for _ in range(2):
        provision(settings(), transport=httpx.MockTransport(handle))
    assert state == {"retain_mission": mission_text(), "reflect_mission": "preserve"}
    assert calls == ["PATCH", "GET", "PATCH", "GET"]


@pytest.mark.parametrize("status", [301, 400, 401, 403, 404, 500])
def test_http_failures_are_safe(status):
    async def handle(request):
        return httpx.Response(status, text="synthetic-canary", headers={"location": "http://evil"})

    with pytest.raises(ProvisionError) as error:
        provision(settings(), transport=httpx.MockTransport(handle))
    assert "synthetic-canary" not in str(error.value)


@pytest.mark.parametrize(
    "body", [None, [], {}, {"config": []}, {"config": {"retain_mission": "wrong"}}]
)
def test_invalid_readback_fails(body):
    async def handle(request):
        return (
            httpx.Response(200, json=body) if body is not None else httpx.Response(200, text="bad")
        )

    with pytest.raises(ProvisionError):
        provision(settings(), transport=httpx.MockTransport(handle))


def test_timeout_is_bounded_and_safe():
    import asyncio

    async def handle(request):
        await asyncio.sleep(1)
        return httpx.Response(200)

    with pytest.raises(ProvisionError, match="unavailable"):
        provision(settings(), transport=httpx.MockTransport(handle), timeout=0.01)


@pytest.mark.parametrize(
    "url", ["http://user:password@engine", "http://engine/?token=secret", "http://engine/#secret"]
)
def test_unsafe_url_rejected(url):
    with pytest.raises(ProvisionError):
        provision(settings(url))


def test_interrupted_readback_rerun_converges():
    state = {}
    fail_once = True

    async def handle(request):
        nonlocal fail_once
        if request.method == "PATCH":
            state.update(json.loads(request.content)["updates"])
        elif fail_once:
            fail_once = False
            raise httpx.ConnectError("synthetic-canary", request=request)
        return httpx.Response(200, json={"config": state})

    transport = httpx.MockTransport(handle)
    with pytest.raises(ProvisionError) as error:
        provision(settings(), transport=transport)
    assert "synthetic-canary" not in str(error.value)
    provision(settings(), transport=transport)
    assert state == {"retain_mission": mission_text()}


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_invalid_deadline(timeout):
    with pytest.raises(ProvisionError):
        provision(settings(), timeout=timeout)


def test_non_ascii_token_is_safe():
    value = settings().model_copy(
        update={"token": __import__("pydantic").SecretStr("synthetic-canary-☃")}
    )
    with pytest.raises(ProvisionError) as error:
        provision(value)
    assert "synthetic-canary" not in str(error.value)
