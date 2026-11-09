"""Cross-source regression through a real engine and fresh stdio consumers.

This exercises data visibility, not an actual Claude Code or Codex conversation.
Only the extraction model is synthetic. A missing required case fails the live gate.
"""

import json
import os
import sys
from datetime import datetime

import anyio
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.classification import AliasProjectClassifier, ProjectRule, ProjectRuleSet
from engineering_memory.ingestion.chatgpt import ChatGPTExportSource
from engineering_memory.ingestion.claude_code.source import ClaudeCodeSessionSource
from engineering_memory.ingestion.pipeline import IngestionPipeline
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.memory.hindsight.store import HindsightStore
from engineering_memory.sanitization import PatternSecretSanitizer
from tests.integration.test_import_recall_e2e import engine, fixture_stats, live  # noqa: F401
from tests.synthetic import chatgpt_export, claude_code

DECISION = "Orchard uses a cobalt relay to isolate worker retries."
REFINEMENT = "Orchard cobalt relay uses amber backoff after three failed retries."
COMPETITOR = "Orchard competitor uses a violet relay instead."


@live
def test_cross_source_import_to_stdio(engine, tmp_path):  # noqa: F811
    settings, _, _ = engine
    archive = LocalRawArchive(tmp_path / "archive")
    state = SQLiteImportState(tmp_path / "state.db")
    state.initialize()
    consumer_cwd = tmp_path / "consumer"
    consumer_cwd.mkdir()
    environment = {k: v for k, v in os.environ.items() if not k.startswith("ENGINEERING_MEMORY_")}
    environment.update(
        ENGINEERING_MEMORY_ARCHIVE_ROOT=str(tmp_path / "archive"),
        ENGINEERING_MEMORY_HINDSIGHT__BASE_URL=str(settings.base_url),
        ENGINEERING_MEMORY_HINDSIGHT__BANK_ID=settings.bank_id,
    )
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from engineering_memory.cli import main; main()", "serve"],
        env=environment,
        cwd=str(consumer_cwd),
    )

    with HindsightStore(settings) as memory:

        def pipeline(project):
            return IngestionPipeline(
                sanitizer=PatternSecretSanitizer(),
                classifier=AliasProjectClassifier(
                    ProjectRuleSet(rules=(ProjectRule(project=project, aliases=("Orchard",)),))
                ),
                archive=archive,
                state=state,
                memory=memory,
                importer_version="synthetic-coding-agent-v1",
                bank=settings.bank_id,
                repository=f"synthetic/{project}",
                user="synthetic",
            )

        async def search(client, source, project="orchard"):
            result = await client.call_tool(
                "search_memory",
                {
                    "query": "Orchard cobalt relay",
                    "tags": [f"project:{project}", f"source:{source}"],
                },
            )
            assert not result.is_error, result
            return result.structured_content["results"]

        async def context(client, document_id, expected, original_time):
            offset, messages = 0, []
            while True:
                result = await client.call_tool(
                    "get_conversation",
                    {"document_id": document_id, "offset": offset, "page_size": 1},
                )
                assert not result.is_error, result
                page = result.structured_content
                assert page["document_id"] == document_id
                assert page["provenance"]["project"] == "orchard"
                assert datetime.fromisoformat(page["started_at"]) == datetime.fromisoformat(
                    original_time
                )
                messages.extend(page["messages"])
                if page["next_offset"] is None:
                    break
                assert page["next_offset"] > offset
                offset = page["next_offset"]
            text = json.dumps(messages)
            assert expected in text
            assert "synthetic-secret-123" not in text
            return messages

        async def scenario():
            with anyio.fail_after(180):
                async with Client(parameters, mode="legacy") as client:
                    tools = await client.list_tools()
                    assert {t.name for t in tools.tools} == {
                        "search_memory",
                        "get_conversation",
                        "get_project_model",
                        "reflect",
                    }
                    assert all(t.annotations.read_only_hint for t in tools.tools)
                    found = await search(client, "chatgpt")
                    assert found and {r["document_id"] for r in found} == {"chatgpt:cross-decision"}
                    assert any(DECISION in r["content"] for r in found)
                    assert all(r["provenance"]["source_id"] == "cross-decision" for r in found)
                    assert all(r["provenance"]["source"] == "chatgpt" for r in found)
                    assert all(r["provenance"]["repository"] == "synthetic/orchard" for r in found)
                    assert all(
                        r["provenance"]["importer_version"] == "synthetic-coding-agent-v1"
                        for r in found
                    )
                    assert all(
                        datetime.fromisoformat(r["started_at"])
                        == datetime.fromisoformat("2020-01-02T00:00:00Z")
                        for r in found
                    )
                    await context(
                        client, "chatgpt:cross-decision", DECISION, "2020-01-02T00:00:00Z"
                    )
                    competing = await search(client, "chatgpt", "cypress")
                    assert competing and {r["document_id"] for r in competing} == {
                        "chatgpt:cross-competitor"
                    }
                    assert not await search(client, "claude-code")
                    assert not await search(client, "chatgpt", "absent")

                # Import only after the first consumer has observed absence.
                imported = orchard.run(ClaudeCodeSessionSource(snapshot))
                assert (imported.imported, imported.failed) == (1, 0)
                before = fixture_stats()
                skipped = orchard.run(ClaudeCodeSessionSource(snapshot))
                after = fixture_stats()
                assert (skipped.imported, skipped.skipped, skipped.failed) == (0, 1, 0)
                assert after["calls"] == before["calls"]
                assert (
                    b"synthetic-secret-123"
                    in archive.load_original("claude-code:cross-refinement").content
                )

                # A new process sees the imported refinement without writing through MCP.
                async with Client(parameters, mode="legacy") as client:
                    found = await search(client, "claude-code")
                    assert found and {r["document_id"] for r in found} == {
                        "claude-code:cross-refinement"
                    }
                    assert any(REFINEMENT in r["content"] for r in found)
                    assert all(r["provenance"]["source"] == "claude-code" for r in found)
                    assert all(r["provenance"]["source_id"] == "cross-refinement" for r in found)
                    assert all(r["provenance"]["project"] == "orchard" for r in found)
                    assert all(
                        datetime.fromisoformat(r["started_at"])
                        == datetime.fromisoformat("2026-03-04T09:30:00Z")
                        for r in found
                    )
                    messages = await context(
                        client, "claude-code:cross-refinement", REFINEMENT, "2026-03-04T09:30:00Z"
                    )
                    assert len(messages) == 2  # Requires paging, not only a first-page check.
                    assert not await search(client, "claude-code", "cypress")
                    assert not await search(client, "codex")

        try:
            orchard = pipeline("orchard")
            for identity, fact, project in [
                ("cross-decision", DECISION, "orchard"),
                ("cross-competitor", COMPETITOR, "cypress"),
            ]:
                export = chatgpt_export.write_directory(
                    tmp_path / identity,
                    [
                        chatgpt_export.linear_record(
                            identity,
                            chatgpt_export.message("user", "Synthetic contract fact: " + fact),
                            create_time=1577923200,
                        )
                    ],
                )
                report = pipeline(project).run(ChatGPTExportSource(export))
                assert (report.imported, report.failed) == (1, 0)
            records = [
                claude_code.record(
                    content=(
                        "Refine the synthetic cobalt relay decision. password=synthetic-secret-123"
                    )
                ),
                claude_code.record(
                    "assistant",
                    "Synthetic contract fact: " + REFINEMENT,
                ),
            ]
            for index, record in enumerate(records):
                record["sessionId"] = "cross-refinement"
                record["uuid"] = f"turn-{index}"
            snapshot = claude_code.write(tmp_path / "refinement.jsonl", records)
            anyio.run(scenario)
        finally:
            state.close()
