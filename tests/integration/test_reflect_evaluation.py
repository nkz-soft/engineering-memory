import json
import sys

import pytest
from mcp.client.stdio import StdioServerParameters
from typer.testing import CliRunner

from engineering_memory.cli import app
from engineering_memory.evaluation import runner

SERVER = """
import json
import os
import sys
from pathlib import Path

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

requests = Path(sys.argv[1])
mode = sys.argv[2]
wire = os.fdopen(os.dup(1), "w", encoding="utf-8")

async def call_tool(context, parameters):
    args = parameters.arguments
    with requests.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps([parameters.name, args]) + "\\n")
    print("PRIVATE_STDERR", file=sys.stderr)
    first = args["query"] == "PRIVATE_QUESTION_0"
    if first and mode == "exit":
        os._exit(7)
    if first and mode == "wire":
        print("PRIVATE_WIRE", file=wire, flush=True)
        await anyio.sleep(60)
    citation = {
        "document_id": "chatgpt:example",
        "provenance": {
            "source": "chatgpt",
            "source_id": "example",
            "project": "example",
            "imported_at": "2026-10-05T10:00:00Z",
            "importer_version": "test",
        },
        "started_at": "2026-10-01T09:00:00Z",
    }
    if parameters.name == "search_memory":
        if first and mode == "pairs":
            return CallToolResult(
                is_error=True, content=[TextContent(type="text", text="PRIVATE_TOOL")]
            )
        await anyio.sleep(0.02)
        payload = {"results": [{**citation, "score": 0.5, "content": "PRIVATE_FACT"}]}
    elif first and mode == "pairs":
        payload = {"status": "insufficient_evidence", "references": []}
    elif mode == "pairs" and args["query"] == "PRIVATE_QUESTION_1":
        payload = {"status": "completed", "answer": "PRIVATE_BAD", "references": []}
    else:
        await anyio.sleep(0.05)
        payload = {"status": "completed", "answer": "PRIVATE_ANSWER", "references": [citation]}
    return CallToolResult(content=[], structured_content=payload)


async def list_tools(context, parameters):
    return ListToolsResult(
        tools=[
            Tool(name=name, input_schema={"type": "object"})
            for name in ("search_memory", "reflect")
        ]
    )


async def serve():
    server = Server("fixture", on_call_tool=call_tool, on_list_tools=list_tools)
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


anyio.run(serve)
"""


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    private = tmp_path / "data"
    private.mkdir()
    requests = tmp_path / "requests.jsonl"
    script = tmp_path / "server.py"
    script.write_text(SERVER, encoding="utf-8")
    dataset = {
        "schema_version": 1,
        "version": "fixture-v1",
        "profile": {
            "engine_version": "fixture-engine",
            "model_id": "fixture-model",
            "corpus_summary": "Two synthetic conversations from October 2026.",
            "project_model_availability": {"example": False},
        },
        "cases": [
            {
                "id": f"case-{index}",
                "kind": kind,
                "project": "example",
                "question": f"PRIVATE_QUESTION_{index}",
                "expected_points": [
                    {
                        "id": "point-1",
                        "text": "PRIVATE_EXPECTATION",
                        "document_ids": ["chatgpt:example", "chatgpt:earlier"],
                    }
                ],
            }
            for index, kind in enumerate(["evolution"] * 3 + ["decision"] * 3 + ["lookup"] * 2)
        ],
    }

    def configure(mode="pairs", *, cases=None, output=None):
        monkeypatch.setattr(
            runner,
            "_server_parameters",
            lambda: StdioServerParameters(
                command=sys.executable, args=[str(script), str(requests), mode]
            ),
        )
        cases = cases or private / "cases.json"
        output = output or private / "run.json"
        cases.write_text(json.dumps(dataset), encoding="utf-8")
        args = ["evaluate", "reflect", "--cases", str(cases), "--output", str(output)]
        return CliRunner().invoke(app, args), output, requests

    return configure, dataset


def test_paired_evaluator_keeps_both_outcomes_after_operation_failures(prepared, caplog):
    configure, dataset = prepared
    result, output, requests = configure()
    assert result.exit_code == 1
    assert "reflection evaluation failed" in result.output
    assert "PRIVATE_" not in result.output + caplog.text
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "complete"
    assert report["case_set_version"] == "fixture-v1"
    assert report["profile"] == dataset["profile"]
    assert report["recall_limit"] == 10
    assert [pair["case_id"] for pair in report["pairs"]] == [f"case-{i}" for i in range(8)]
    assert [json.loads(line) for line in requests.read_text(encoding="utf-8").splitlines()] == [
        call
        for i in range(8)
        for call in (
            [
                "search_memory",
                {"query": f"PRIVATE_QUESTION_{i}", "tags": ["project:example"], "limit": 10},
            ],
            ["reflect", {"query": f"PRIVATE_QUESTION_{i}", "project": "example"}],
        )
    ]
    first, malformed, completed = report["pairs"][:3]
    assert first["search_memory"]["failure"] == "tool_error"
    assert first["reflect"]["status"] == "insufficient_evidence"
    assert "answer" not in first["reflect"]
    assert malformed["reflect"]["failure"] == "invalid_response"
    assert "answer" not in malformed["reflect"]
    assert completed["search_memory"]["results"][0]["content"] == "PRIVATE_FACT"
    assert completed["reflect"]["references"][0]["document_id"] == "chatgpt:example"
    assert completed["reflect"]["answer"] == "PRIVATE_ANSWER"
    assert completed["search_memory"]["elapsed_ms"] >= 10
    assert completed["reflect"]["elapsed_ms"] >= 30
    assert "PRIVATE_TOOL" not in output.read_text(encoding="utf-8")


@pytest.mark.parametrize("mode", ["exit", "wire"])
def test_paired_evaluator_marks_unattempted_calls_after_transport_loss(prepared, caplog, mode):
    configure, _ = prepared
    result, output, requests = configure(mode)
    assert result.exit_code == 1
    assert "reflection evaluation failed" in result.output
    assert "PRIVATE_" not in result.output + caplog.text
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "incomplete"
    assert len(report["pairs"]) == 8
    first, *rest = report["pairs"]
    assert first["search_memory"]["status"] == "failed"
    assert first["search_memory"]["failure"] == "transport"
    assert first["search_memory"]["elapsed_ms"] >= 0
    for outcome in [
        first["reflect"],
        *(pair[op] for pair in rest for op in ("search_memory", "reflect")),
    ]:
        assert outcome["status"] == "unattempted"
        assert "elapsed_ms" not in outcome
    assert len(requests.read_text(encoding="utf-8").splitlines()) == 1


@pytest.mark.parametrize("target", ["cases", "output"])
def test_paired_evaluator_rejects_paths_outside_data(prepared, tmp_path, target):
    configure, _ = prepared
    outside = tmp_path / "private-outside-data.json"
    result, output, requests = configure(**{target: outside})
    assert result.exit_code == 1
    assert "invalid reflection evaluation input" in result.output
    assert not output.exists()
    assert not requests.exists()


@pytest.mark.parametrize("field", ["scope", "duplicate", "profile", "expectations", "count"])
def test_paired_evaluator_rejects_invalid_case_sets_before_calls(prepared, field):
    configure, dataset = prepared
    if field == "scope":
        dataset["cases"][0]["project"] = "project:example"
    elif field == "duplicate":
        dataset["cases"][0]["id"] = dataset["cases"][1]["id"]
    elif field == "profile":
        dataset["profile"]["project_model_availability"] = {}
    elif field == "expectations":
        dataset["cases"][0]["expected_points"][0]["document_ids"] = []
    else:
        dataset["cases"].pop()
    result, output, requests = configure()
    assert result.exit_code == 1
    assert "invalid reflection evaluation input" in result.output
    assert not output.exists()
    assert not requests.exists()


def test_paired_evaluator_replaces_prior_report_on_success(prepared, tmp_path):
    configure, _ = prepared
    output = tmp_path / "data" / "run.json"
    output.write_text("prior", encoding="utf-8")
    result, _, _ = configure("success", output=output)
    assert result.exit_code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "complete"
    assert all(
        pair[operation]["status"] == "completed"
        for pair in report["pairs"]
        for operation in ("search_memory", "reflect")
    )


def test_paired_evaluator_removes_temporary_report_if_replacement_fails(prepared, tmp_path):
    configure, _ = prepared
    private = tmp_path / "data"
    output = private / "run.json"
    output.mkdir()
    existing = output / "prior"
    existing.write_text("prior", encoding="utf-8")
    result, _, requests = configure("success", output=output)
    assert result.exit_code == 1
    assert "report write failed" in result.output
    assert existing.read_text(encoding="utf-8") == "prior"
    assert len(requests.read_text(encoding="utf-8").splitlines()) == 16
    assert sorted(path.name for path in private.iterdir()) == ["cases.json", "run.json"]


def test_paired_evaluator_rejects_escaping_symlink(prepared, tmp_path):
    configure, _ = prepared
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "data" / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    result, output, requests = configure(output=link / "run.json")
    assert result.exit_code == 1
    assert "invalid reflection evaluation input" in result.output
    assert not output.exists()
    assert not requests.exists()
