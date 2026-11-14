import json
from unittest.mock import Mock

import httpx
import pytest
from typer.testing import CliRunner

from engineering_memory.access.deep_recall import SynthesisLimit
from engineering_memory.access.service import AccessError
from engineering_memory.cli import app
from engineering_memory.settings import load_access_settings


def test_cli_emits_shared_payload(monkeypatch):
    from engineering_memory.cli import runtime

    service = Mock()
    payload = {"status": "partial", "timeline": [], "coverage": {}, "uncertainty": []}
    service.deep_recall.return_value = payload
    factory = Mock(return_value=service)
    monkeypatch.setattr(runtime, "make_read_access", factory, raising=False)
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    result = CliRunner().invoke(app, ["deep-recall", "Why?", "--project", "demo", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == payload
    service.deep_recall.assert_called_once_with(query="Why?", project="demo")


def test_endpoint_is_opt_in_and_only_receives_manifest(monkeypatch):
    from engineering_memory.access.synthesis import OpenAICompatibleSynthesizer

    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    assert load_access_settings().deep_recall is None
    monkeypatch.setenv("ENGINEERING_MEMORY_DEEP_RECALL__BASE_URL", "https://local.test/v1")
    monkeypatch.setenv("ENGINEERING_MEMORY_DEEP_RECALL__MODEL", "test-model")
    monkeypatch.setenv("ENGINEERING_MEMORY_DEEP_RECALL__API_KEY", "test-key")
    settings = load_access_settings().deep_recall

    def receive(request):
        assert request.url == "https://local.test/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert json.loads(body["messages"][1]["content"]) == {
            "question": "why?",
            "passages": [{"selector": "1", "text": "safe", "timestamp": None}],
        }
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"timeline":[]}'}}]})

    adapter = OpenAICompatibleSynthesizer(settings, transport=httpx.MockTransport(receive))
    assert adapter.synthesize("why?", {"1": "safe"}, {"1": None}) == {"timeline": []}


@pytest.mark.parametrize("code,size", [(302, 0), (200, 17000)])
def test_rejects_redirects_and_oversize_responses(monkeypatch, code, size):
    from engineering_memory.access.synthesis import OpenAICompatibleSynthesizer

    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_DEEP_RECALL__BASE_URL", "https://local.test/v1")
    monkeypatch.setenv("ENGINEERING_MEMORY_DEEP_RECALL__MODEL", "test-model")
    handler = Mock(
        return_value=httpx.Response(
            code, content=b"x" * size, headers={"Location": "https://foreign.test"}
        )
    )
    adapter = OpenAICompatibleSynthesizer(
        load_access_settings().deep_recall, transport=httpx.MockTransport(handler)
    )
    if code == 302:
        with pytest.raises(AccessError, match="unavailable"):
            adapter.synthesize("why?", {"1": "safe"}, {"1": None})
    else:
        with pytest.raises(SynthesisLimit, match="synthesis_response_limit"):
            adapter.synthesize("why?", {"1": "safe"}, {"1": None})
    handler.assert_called_once()


@pytest.mark.parametrize("failure", ["timeout", "stream_limit"])
def test_synthesis_stops_on_transport_budgets(monkeypatch, failure):
    import anyio

    from engineering_memory.access import synthesis

    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_DEEP_RECALL__BASE_URL", "https://local.test/v1")
    monkeypatch.setenv("ENGINEERING_MEMORY_DEEP_RECALL__MODEL", "test-model")
    settings = load_access_settings().deep_recall
    consumed = []

    class Oversize(httpx.AsyncByteStream):
        async def __aiter__(self):
            for index in range(32):
                consumed.append(index)
                yield b"x" * 1024

    async def receive(request):
        if failure == "timeout":
            await anyio.sleep_forever()
        return httpx.Response(200, stream=Oversize())

    if failure == "timeout":
        monkeypatch.setattr(synthesis, "_TIMEOUT_SECONDS", 0.01)
    adapter = synthesis.OpenAICompatibleSynthesizer(
        settings, transport=httpx.MockTransport(receive)
    )
    code = "synthesis_timeout" if failure == "timeout" else "synthesis_response_limit"
    with pytest.raises(SynthesisLimit, match=code):
        adapter.synthesize("why?", {"1": "safe"}, {"1": None})
    if failure == "stream_limit":
        assert len(consumed) == 17
