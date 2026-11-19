"""Exercise the handoff CLI and configured synthesis transport."""

import json
from unittest.mock import Mock

import httpx
from typer.testing import CliRunner

from engineering_memory.access.service import SynthesisUnconfigured
from engineering_memory.access.synthesis import OpenAICompatibleSynthesizer
from engineering_memory.cli import app, runtime
from engineering_memory.settings import DeepRecallSettings


def test_cli_prints_the_shared_markdown(monkeypatch):
    read = Mock(return_value={"markdown": "# Session handoff\n"})
    monkeypatch.setattr(runtime, "read_session_handoff", read)
    result = CliRunner().invoke(
        app,
        [
            "session-handoff",
            "claude-code:one",
            "--project",
            "demo",
            "--explorer-origin",
            "http://127.0.0.1:8000",
        ],
    )
    assert result.exit_code == 0
    assert result.stdout == "# Session handoff\n"
    assert result.stderr == ""
    read.assert_called_once_with(
        document_id="claude-code:one", project="demo", link_origin="http://127.0.0.1:8000"
    )


def test_cli_unconfigured_has_guidance_and_no_stdout(monkeypatch):
    monkeypatch.setattr(runtime, "read_session_handoff", Mock(side_effect=SynthesisUnconfigured()))
    result = CliRunner().invoke(app, ["session-handoff", "claude-code:one", "--project", "demo"])
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "ENGINEERING_MEMORY_DEEP_RECALL__BASE_URL" in result.stderr


def test_adapter_uses_handoff_schema_and_does_not_pass_tools():
    def receive(request):
        body = json.loads(request.content)
        assert "entries" in body["messages"][0]["content"]
        assert "tools" not in body
        assert json.loads(body["messages"][1]["content"])["passages"] == [
            {"selector": "1", "text": "safe", "timestamp": None}
        ]
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"entries":[]}'}}]})

    settings = DeepRecallSettings(base_url="http://127.0.0.1:8010", model="test")
    adapter = OpenAICompatibleSynthesizer(settings, transport=httpx.MockTransport(receive))
    assert adapter.synthesize_handoff({"1": "safe"}, {"1": None}) == {"entries": []}
