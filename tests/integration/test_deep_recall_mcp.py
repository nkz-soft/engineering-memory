"""Import native Claude Code and Codex snapshots and query them over stdio."""

import json
import os
import sys
from contextlib import closing
from pathlib import Path

import anyio
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters
from typer.testing import CliRunner

from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.classification import AliasProjectClassifier, ProjectRule, ProjectRuleSet
from engineering_memory.cli import app, runtime
from engineering_memory.ingestion.claude_code import ClaudeCodeSessionSource
from engineering_memory.ingestion.codex import CodexSessionSource
from engineering_memory.ingestion.pipeline import IngestionPipeline
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.sanitization import PatternSecretSanitizer
from tests.fakes.store import InMemoryMemoryStore
from tests.synthetic import claude_code, codex

PROPOSED = "Cache results daily to reduce load."
REVISED = "Cache results hourly because daily results went stale."
FOREIGN = "Cache results weekly in the other project."


class FixtureSynthesis:
    def synthesize(self, query, passages, times):
        assert FOREIGN not in passages.values()
        assert "synthetic-secret-123" not in str(passages)
        return {
            "timeline": [
                {"text": text.split(" password=")[0], "citations": [{"selector": key}]}
                for key, text in reversed(list(passages.items()))
                if text.startswith((PROPOSED, REVISED))
            ]
        }


def launch_fixture_server(archive_root):
    from engineering_memory.access.server import run_stdio
    from engineering_memory.access.service import MemoryAccess

    archive = LocalRawArchive(Path(archive_root))
    memory = InMemoryMemoryStore()
    for document in ("claude-code:original", "codex:revised", "codex:foreign"):
        memory.retain(archive.load(document))
    run_stdio(MemoryAccess(memory, archive, synthesis=FixtureSynthesis()))


def test_deep_recall_after_import_on_both_surfaces(tmp_path, monkeypatch):
    archive = LocalRawArchive(tmp_path / "archive")
    memory = InMemoryMemoryStore()
    initial = claude_code.record(content=PROPOSED + " password=synthetic-secret-123")
    initial["sessionId"] = "original"
    claude_path = claude_code.write(tmp_path / "initial.jsonl", [initial])

    def codex_snapshot(identity, text):
        when = "2026-04-04T09:30:00Z"
        records = [
            codex.record("session_meta", id=identity, timestamp=when, cwd="/work/orchard"),
            codex.message("assistant", text),
        ]
        for record in records:
            record["timestamp"] = when
        return codex.write(tmp_path / f"{identity}.jsonl", records)

    with closing(SQLiteImportState(tmp_path / "state.db")) as state:
        state.initialize()
        for source, project in (
            (ClaudeCodeSessionSource(claude_path), "orchard"),
            (CodexSessionSource(codex_snapshot("revised", REVISED)), "orchard"),
            (CodexSessionSource(codex_snapshot("foreign", FOREIGN)), "orchard-extra"),
        ):
            pipeline = IngestionPipeline(
                sanitizer=PatternSecretSanitizer(),
                classifier=AliasProjectClassifier(
                    ProjectRuleSet(rules=(ProjectRule(project=project, aliases=("Cache",)),))
                ),
                archive=archive,
                state=state,
                memory=memory,
                bank="engineering-global",
                importer_version="synthetic-v1",
                repository="synthetic/orchard",
                user="synthetic",
            )
            report = pipeline.run(source)
            assert (report.imported, report.failed) == (1, 0)

    from engineering_memory.access.service import MemoryAccess

    monkeypatch.setattr(
        runtime,
        "make_read_access",
        lambda resources: MemoryAccess(memory, archive, synthesis=FixtureSynthesis()),
    )
    cli = CliRunner().invoke(app, ["deep-recall", "Cache", "--project", "orchard", "--json"])
    assert cli.exit_code == 0, cli.output
    cli_result = json.loads(cli.stdout)
    assert cli_result["status"] == "completed"
    assert [entry["text"] for entry in cli_result["timeline"]] == [PROPOSED, REVISED]

    parameters = StdioServerParameters(
        command=sys.executable,
        args=[
            "-c",
            "import sys; from tests.integration.test_deep_recall_mcp import "
            "launch_fixture_server; launch_fixture_server(sys.argv[1])",
            str(tmp_path / "archive"),
        ],
        cwd=str(Path(__file__).resolve().parents[2]),
        env={
            key: value
            for key, value in os.environ.items()
            if not key.startswith("ENGINEERING_MEMORY_")
        },
    )

    async def scenario():
        with anyio.fail_after(30):
            async with Client(parameters, mode="legacy") as client:
                result = await client.call_tool(
                    "deep_recall", {"query": "Cache", "project": "orchard"}
                )
                assert not result.is_error
                assert result.structured_content == cli_result
                anchors = [entry["citations"][0] for entry in cli_result["timeline"]]
                assert [a["document_id"] for a in anchors] == [
                    "claude-code:original",
                    "codex:revised",
                ]
                for anchor in anchors:
                    page = await client.call_tool(
                        "get_conversation",
                        {
                            "document_id": anchor["document_id"],
                            "offset": anchor["message_index"],
                            "page_size": 1,
                        },
                    )
                    assert not page.is_error
                    assert anchor["quote"] in page.structured_content["messages"][0]["text"]

    anyio.run(scenario)
