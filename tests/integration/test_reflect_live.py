"""Exercise reflect against the pinned engine and a deterministic model fixture."""

import json
import os
import sys

import anyio
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

from engineering_memory.archive import OriginalPayload
from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.memory.hindsight.store import HindsightStore
from tests.contracts import conversations
from tests.integration.test_import_recall_e2e import engine, live  # noqa: F401

QUERY = "Synthetic reflect contract: how did the Orchard relay decision change?"
DECISIONS = {
    "initial-relay": "Orchard initially used a cobalt relay.",
    "revised-relay": "Orchard later replaced the cobalt relay with an amber relay.",
}


@live
def test_reflect_returns_openable_scoped_evidence(engine, tmp_path):  # noqa: F811
    settings, http, root = engine
    archive_path = tmp_path / "archive"
    archive = LocalRawArchive(archive_path)
    with HindsightStore(settings) as store:
        for identity, text in DECISIONS.items():
            record = conversations.enrich(
                conversations.conversation(identity, text="Synthetic contract fact: " + text),
                project="orchard",
            )
            archive.store(
                record, OriginalPayload(content=b"synthetic original", media_type="text/plain")
            )
            store.retain(record)
        competitor = conversations.enrich(
            conversations.conversation(
                "competing-relay",
                text="Synthetic contract fact: Orchard competitor uses a magenta relay.",
            ),
            project="competing",
        )
        store.retain(competitor)  # A matched fact whose normalized archive record is absent.

    wire = http.post(
        root + "/reflect",
        json={
            "query": QUERY,
            "tags": ["project:orchard"],
            "tags_match": "all_strict",
            "budget": "mid",
            "include": {"facts": {}},
        },
    )
    wire.raise_for_status()
    expected = {"chatgpt:" + identity for identity in DECISIONS}
    facts = wire.json()["based_on"]["memories"]
    assert {fact["document_id"] for fact in facts} == expected
    for fact in facts:
        assert "project:orchard" in fact["tags"]
        provenance = json.loads(fact["metadata"]["engineering_memory.provenance"])
        assert provenance["project"] == "orchard"
        assert fact["document_id"] == f"chatgpt:{provenance['source_id']}"

    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("ENGINEERING_MEMORY_")
    }
    environment.update(
        ENGINEERING_MEMORY_ARCHIVE_ROOT=str(archive_path),
        ENGINEERING_MEMORY_HINDSIGHT__BASE_URL=str(settings.base_url),
        ENGINEERING_MEMORY_HINDSIGHT__BANK_ID=settings.bank_id,
    )
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from engineering_memory.cli import main; main()", "serve"],
        env=environment,
        cwd=str(tmp_path),
    )

    async def scenario():
        with anyio.fail_after(120):
            async with Client(parameters, mode="legacy") as client:
                result = await client.call_tool("reflect", {"query": QUERY, "project": "orchard"})
                assert not result.is_error, result
                result = result.structured_content
                assert result["status"] == "completed"
                assert "cobalt" in result["answer"] and "amber" in result["answer"]
                assert "magenta" not in result["answer"]
                assert {reference["document_id"] for reference in result["references"]} == expected

                for reference in result["references"]:
                    source = await client.call_tool(
                        "get_conversation", {"document_id": reference["document_id"]}
                    )
                    assert not source.is_error, source
                    page = source.structured_content
                    assert page["provenance"] == reference["provenance"]
                    assert page["started_at"] == reference["started_at"]
                    assert any(
                        DECISIONS[page["provenance"]["source_id"]] in message["text"]
                        for message in page["messages"]
                    )

                missing = await client.call_tool(
                    "reflect", {"query": QUERY, "project": "competing"}
                )
                assert not missing.is_error, missing
                assert missing.structured_content == {
                    "status": "insufficient_evidence",
                    "references": [],
                }

    anyio.run(scenario)
