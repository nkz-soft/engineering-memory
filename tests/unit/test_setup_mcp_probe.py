import sys
import time
from pathlib import Path

import pytest

from engineering_memory import setup_mcp_probe

RESPONDER = r"""
import json
import os
import sys
import time
from pathlib import Path

mode = sys.argv[1]
assert "FIXTURE_PRIVATE_TOKEN" not in os.environ
assert "ENGINEERING_MEMORY_HINDSIGHT__API_KEY" not in os.environ
if mode == "hang":
    time.sleep(60)
if mode == "bad":
    print("sensitive fixture diagnostic", file=sys.stderr)
    raise SystemExit(1)
notified = False
for line in sys.stdin:
    request = json.loads(line)
    method = request["method"]
    if method == "initialize":
        result = {"protocolVersion": request["params"]["protocolVersion"],
                  "capabilities": {"tools": {}}, "serverInfo": {"name": "fixture", "version": "1"}}
    elif method == "notifications/initialized":
        notified = True
        continue
    elif method == "tools/list":
        assert notified
        names = ["search_memory"] if mode == "missing" else ["search_memory", "get_conversation"]
        result = {"tools": [{"name": name, "inputSchema": {"type": "object"}} for name in names]}
    else:
        raise AssertionError("setup must never call a tool")
    print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
"""


@pytest.mark.parametrize(
    ("mode", "expected"), [("good", "passed"), ("missing", "missing-tools"), ("bad", "failed")]
)
def test_probe_requires_each_tool_after_initialize(tmp_path, monkeypatch, capsys, mode, expected):
    monkeypatch.setenv("FIXTURE_PRIVATE_TOKEN", "fixture")
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__API_KEY", "fixture")
    script = tmp_path / "fixture server.py"
    script.write_text(RESPONDER, encoding="utf-8")
    status = setup_mcp_probe._probe(Path(sys.executable), (str(script), mode), timeout=4)
    assert status == expected
    assert "sensitive fixture diagnostic" not in capsys.readouterr().err


def test_hung_spawn_is_stopped(tmp_path):
    script = tmp_path / "fixture server.py"
    script.write_text(RESPONDER, encoding="utf-8")
    started = time.monotonic()
    status = setup_mcp_probe._probe(Path(sys.executable), (str(script), "hang"), timeout=0.2)
    assert status == "timeout"
    assert time.monotonic() - started < 8


def test_missing_executable_returns_safe_status(tmp_path):
    assert setup_mcp_probe.probe(tmp_path / "unavailable") == "failed"
