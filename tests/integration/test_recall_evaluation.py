import json
import sys
from pathlib import Path

import pytest
from mcp.client.stdio import StdioServerParameters
from typer.testing import CliRunner

from engineering_memory.cli import app
from engineering_memory.evaluation import runner

DATA = Path(__file__).resolve().parents[2] / "evaluation" / "recall-v1"

SERVER = """
import json
import os
import sys
from pathlib import Path

from engineering_memory.access.server import run_stdio
from engineering_memory.access.service import AccessError

queries_path = Path(sys.argv[1])
mode = sys.argv[2]
wire = os.fdopen(os.dup(1), "w", encoding="utf-8")


class Access:
    def search_memory(self, **kwargs):
        with queries_path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(kwargs) + "\\n")
        print("PRIVATE_SERVER_SENTINEL", file=sys.stderr)
        if mode == "fail":
            raise AccessError("PRIVATE_TOOL_SENTINEL")
        if mode == "wire":
            print("PRIVATE_WIRE_SENTINEL", file=wire, flush=True)
        if mode == "notification":
            print(json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/message",
                "params": {"level": "PRIVATE_NOTIFY_SENTINEL", "data": "PRIVATE_DATA_SENTINEL"},
            }), file=wire, flush=True)
        if mode == "malformed":
            return {"results": [{"document_id": "chatgpt:example"}]}
        return {
            "results": [{"document_id": "chatgpt:example", "content": "PRIVATE_TEXT_SENTINEL"}]
            if mode == "text" else []
        }

    get_conversation = get_project_model = search_memory


run_stdio(Access())
"""


@pytest.mark.parametrize("mode", ["empty", "text", "fail", "malformed", "wire", "notification"])
def test_recall_cli_over_stdio(tmp_path, monkeypatch, caplog, mode):
    script = tmp_path / "server.py"
    script.write_text(SERVER, encoding="utf-8")
    queries = tmp_path / "queries.jsonl"
    monkeypatch.setattr(
        runner,
        "_server_parameters",
        lambda: StdioServerParameters(
            command=sys.executable, args=[str(script), str(queries), mode]
        ),
    )
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "run_id": "test",
                "engine_version": "1.2.0",
                "extractor_id": "test-model",
                "mission_sha256": "0" * 64,
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    output.write_text("prior", encoding="utf-8")
    result = CliRunner().invoke(
        app,
        [
            "evaluate",
            "recall",
            "--benchmark",
            str(DATA / "benchmark.json"),
            "--profile",
            str(profile),
            "--output",
            str(output),
        ],
    )

    requests = [json.loads(line) for line in queries.read_text(encoding="utf-8").splitlines()]
    assert all(
        row["tags"] == ["project:recall-benchmark"] and row["limit"] == 10 for row in requests
    )
    assert "PRIVATE_" not in result.output
    assert "PRIVATE_" not in caplog.text
    if mode in {"fail", "malformed", "wire"}:
        assert result.exit_code == 1
        assert "recall failed" in result.output
        assert len(requests) == 1
        assert output.read_text(encoding="utf-8") == "prior"
    else:
        assert result.exit_code == 0, result.output
        report = json.loads(output.read_text(encoding="utf-8"))
        assert len(requests) == len(report["questions"]) >= 30
        assert report["overall_score"] == 0
        assert len(report["category_scores"]) == 7
        assert "PRIVATE_" not in output.read_text(encoding="utf-8")
