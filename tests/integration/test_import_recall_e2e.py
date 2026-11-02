"""A real import must leave a recallable decision, with its history intact.

Only extraction is synthetic. Raw engine inspection supplements normal adapter
recall, because the public boundary intentionally hides tags and engine dates.
"""

import json
import os
from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from typer.testing import CliRunner

from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.classification import AliasProjectClassifier, ProjectRule, ProjectRuleSet
from engineering_memory.cli import app
from engineering_memory.ingestion.chatgpt import ChatGPTExportSource
from engineering_memory.ingestion.pipeline import IngestionPipeline
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.ingestion.state import ImportStatus
from engineering_memory.memory.hindsight import store as wire
from engineering_memory.memory.hindsight.provision import provision
from engineering_memory.memory.hindsight.serialization import decode_result
from engineering_memory.memory.hindsight.store import HindsightStore
from engineering_memory.memory.interface import MemoryStoreRejected
from engineering_memory.normalization import (
    ConversationType,
    ProjectTag,
    Source,
    SourceTag,
    TypeTag,
    UserTag,
)
from engineering_memory.sanitization import PatternSecretSanitizer
from engineering_memory.settings import HindsightSettings
from tests.synthetic import chatgpt_export as synth

DOCUMENT = "chatgpt:synthetic-e2e-decision"
ORIGINAL = datetime(2020, 1, 2, tzinfo=UTC)
DECISION = "Orchard uses a cobalt relay to isolate worker retries."
TAGS = {"source:chatgpt", "project:orchard", "type:conversation", "user:synthetic"}
EXPECTED = {
    "source": "chatgpt",
    "source_id": "synthetic-e2e-decision",
    "project": "orchard",
    "repository": "synthetic/orchard",
    "title": "Synthetic Orchard decision",
    "importer_version": "synthetic-e2e-v1",
}
live = pytest.mark.skipif(
    os.environ.get("ENGINEERING_MEMORY_LIVE_E2E") != "1",
    reason="requires isolated testcontainers end-to-end stack",
)


def assert_fact(
    fact,
    earliest,
    latest,
    *,
    repository="synthetic/orchard",
    importer_version="synthetic-e2e-v1",
    expected_tags=None,
):
    """Expectations are independent of item_for/enrich and the archive output."""
    assert fact["document_id"] == DOCUMENT, "stable document identity"
    assert DECISION in fact["text"], "known engineering decision"
    expected_tags = TAGS if expected_tags is None else expected_tags
    assert set(fact.get("tags", [])) == expected_tags, "complete tag set"
    metadata = fact.get("metadata", {})
    provenance = json.loads(metadata.get("engineering_memory.provenance", "{}"))
    expected = {**EXPECTED, "repository": repository, "importer_version": importer_version}
    for key, value in expected.items():
        assert provenance.get(key) == value, f"provenance {key}"
    assert "imported_at" in provenance, "provenance imported_at"
    imported_at = datetime.fromisoformat(provenance["imported_at"])
    assert earliest <= imported_at <= latest, "provenance import time"
    assert "mentioned_at" in fact, "original temporal grounding"
    assert datetime.fromisoformat(fact["mentioned_at"]) == ORIGINAL, "original temporal grounding"
    assert "engineering_memory.started_at" in metadata, "original metadata timestamp"
    assert datetime.fromisoformat(metadata["engineering_memory.started_at"]) == ORIGINAL, (
        "original metadata timestamp"
    )
    # Verify the production decoder, rather than only a test's raw JSON reading.
    recalled = decode_result(fact, sorted(expected_tags))
    for key, value in expected.items():
        assert recalled.provenance.model_dump(mode="json")[key] == value, f"decoded {key}"
    assert DECISION in recalled.content


@pytest.fixture
def engine():
    url = os.environ["ENGINEERING_MEMORY_LIVE_STORE_URL"]
    bank = "synthetic-e2e-" + uuid4().hex
    settings = HindsightSettings(base_url=url, bank_id=bank)
    with httpx.Client(base_url=url, trust_env=False, timeout=30) as client:
        root = f"/v1/default/banks/{bank}"
        try:
            assert client.get(root + "/config").status_code == 404, "bank must start clean"
            provision(settings)
            yield settings, client, root
        finally:
            assert client.delete(root).status_code in {200, 204, 404}, "scratch bank cleanup"


def write_export(tmp_path):
    record = synth.linear_record(
        "synthetic-e2e-decision",
        synth.message("user", "Synthetic contract fact: " + DECISION),
        title="Synthetic Orchard decision",
        create_time=ORIGINAL.timestamp(),
        update_time=ORIGINAL.timestamp(),
    )
    export = tmp_path / "export"
    synth.write_directory(export, [record])
    return record, export


def import_decision(tmp_path, settings):
    record, export = write_export(tmp_path)
    archive = LocalRawArchive(tmp_path / "archive")
    state = SQLiteImportState(tmp_path / "state.db")
    state.initialize()
    earliest = datetime.now(UTC)
    try:
        with HindsightStore(settings) as memory:
            pipeline = IngestionPipeline(
                sanitizer=PatternSecretSanitizer(),
                classifier=AliasProjectClassifier(
                    ProjectRuleSet(rules=(ProjectRule(project="orchard", aliases=("Orchard",)),))
                ),
                archive=archive,
                state=state,
                memory=memory,
                importer_version="synthetic-e2e-v1",
                bank=settings.bank_id,
                repository="synthetic/orchard",
                user="synthetic",
            )
            result = pipeline.run(ChatGPTExportSource(export))
            assert (result.imported, result.failed) == (1, 0), result
            assert (
                state.find(Source.CHATGPT, "synthetic-e2e-decision").status == ImportStatus.IMPORTED
            )
            assert json.loads(archive.load_original(DOCUMENT).content) == record
            archived = archive.load(DOCUMENT)
            assert archived.conversation.started_at == ORIGINAL
            assert DECISION in archived.conversation.messages[0].text
            assert {str(t) for t in archived.tags} == TAGS
            assert archived.provenance.repository == "synthetic/orchard"
            # The second ordinary import skips and preserves the stored identity.
            assert pipeline.run(ChatGPTExportSource(export)).skipped == 1
    finally:
        state.close()
    return earliest, datetime.now(UTC)


def raw_fact(client, root):
    response = client.post(
        root + "/memories/recall",
        json={"query": "Orchard cobalt relay", "types": ["world"], "budget": "high"},
    )
    response.raise_for_status()
    results = response.json()["results"]
    matching = [fact for fact in results if fact["document_id"] == DOCUMENT]
    assert matching, "import must produce a recallable decision"
    return matching[0]


@live
def test_import_and_recall(engine, tmp_path, monkeypatch):
    settings, client, root = engine
    record, export = write_export(tmp_path)
    rules = tmp_path / "projects.toml"
    rules.write_text('[[project]]\nproject = "orchard"\naliases = ["Orchard"]\n')
    for name, value in {
        "IMPORT_STATE_PATH": str(tmp_path / "state.db"),
        "ARCHIVE_ROOT": str(tmp_path / "archive"),
        "PROJECT_RULES_PATH": str(rules),
        "HINDSIGHT__BASE_URL": str(settings.base_url),
        "HINDSIGHT__BANK_ID": settings.bank_id,
        "LLM__BASE_URL": os.environ["CONTRACT_FIXTURE_URL"] + "/v1",
    }.items():
        monkeypatch.setenv("ENGINEERING_MEMORY_" + name, value)

    def invoke(args):
        result = CliRunner().invoke(app, [*args, "--json"])
        assert result.exit_code == 0, (result.output, result.exception)
        return json.loads(result.stdout)

    earliest = datetime.now(UTC)
    assert invoke(["provision"])["mission_verified"]
    assert invoke(["import", "--export", str(export)])["imported"] == 1
    latest = datetime.now(UTC)
    assert invoke(["status"])["imported"] == 1
    assert invoke(["import", "--export", str(export)])["skipped"] == 1
    fact = raw_fact(client, root)
    # CLI supplies the installed version and has no repository argument.
    from importlib.metadata import version

    # Compare via explicit argument rather than deriving expectations from archive.
    cli_version = version("engineering-memory")
    assert_fact(
        fact,
        earliest,
        latest,
        repository=None,
        importer_version=cli_version,
        expected_tags={"source:chatgpt", "project:orchard", "type:conversation"},
    )
    archive = LocalRawArchive(tmp_path / "archive")
    assert json.loads(archive.load_original(DOCUMENT).content) == record
    assert archive.load(DOCUMENT).conversation.started_at == ORIGINAL
    with HindsightStore(settings) as memory:
        assert any(DECISION in r.content for r in memory.recall("cobalt relay"))


@live
def test_pipeline_known_repository_and_tags(engine, tmp_path):
    settings, client, root = engine
    earliest, latest = import_decision(tmp_path, settings)
    fact = raw_fact(client, root)
    assert_fact(fact, earliest, latest)
    tags = (
        SourceTag(value=Source.CHATGPT),
        ProjectTag(value="orchard"),
        TypeTag(value=ConversationType.CONVERSATION),
        UserTag(value="synthetic"),
    )
    with HindsightStore(settings) as memory:
        for scope in [tags, *((tag,) for tag in tags)]:
            recalled = memory.recall("cobalt relay", tags=scope)
            assert recalled and any(DECISION in match.content for match in recalled)
            assert recalled[0].provenance.model_dump(mode="json") == json.loads(
                fact["metadata"]["engineering_memory.provenance"]
            )
        mismatches = (
            SourceTag(value=Source.CODEX),
            ProjectTag(value="disjoint"),
            TypeTag(value=ConversationType.DECISION),
            UserTag(value="disjoint"),
        )
        for index, mismatch in enumerate(mismatches):
            scope = (*tags[:index], mismatch, *tags[index + 1 :])
            assert memory.recall("cobalt relay", tags=scope) == (), f"disjoint {mismatch}"
    with httpx.Client(trust_env=False, timeout=10) as fixture:
        stats = fixture.get(os.environ["CONTRACT_FIXTURE_URL"] + "/stats").json()
        assert stats["errors"] == 0 and stats["calls"] >= 1, "real extraction processing"


@live
def test_wire_timestamp_omission_is_detected(engine, tmp_path, monkeypatch):
    original_item = wire.item_for

    def omit_timestamp(enriched):
        item = original_item(enriched)
        del item["timestamp"]
        return item

    monkeypatch.setattr(wire, "item_for", omit_timestamp)
    settings, client, root = engine
    earliest, latest = import_decision(tmp_path, settings)
    fact = raw_fact(client, root)
    # Metadata still has historical time: the assertion must check real grounding.
    assert datetime.fromisoformat(fact["metadata"]["engineering_memory.started_at"]) == ORIGINAL
    with pytest.raises(AssertionError, match="original temporal grounding"):
        assert_fact(fact, earliest, latest)


def synthetic_evidence():
    """Independently authored positive control for omission sensitivity."""
    return {
        "document_id": DOCUMENT,
        "text": DECISION,
        "tags": sorted(TAGS),
        "mentioned_at": "2020-01-02T00:00:00Z",
        "metadata": {
            "engineering_memory.version": "1",
            "engineering_memory.started_at": "2020-01-02T00:00:00Z",
            "engineering_memory.provenance": json.dumps(
                {
                    **EXPECTED,
                    "imported_at": "2026-01-01T00:00:00Z",
                }
            ),
        },
    }


def check_synthetic(fact):
    assert_fact(fact, datetime(2025, 1, 1, tzinfo=UTC), datetime(2027, 1, 1, tzinfo=UTC))


def test_evidence_positive_control():
    check_synthetic(synthetic_evidence())


@pytest.mark.parametrize("field", [*EXPECTED, "imported_at"])
def test_provenance_omission_is_detected(field):
    fact = deepcopy(synthetic_evidence())
    metadata = fact["metadata"]
    provenance = json.loads(metadata["engineering_memory.provenance"])
    del provenance[field]
    metadata["engineering_memory.provenance"] = json.dumps(provenance)
    with pytest.raises(AssertionError, match="provenance " + field):
        check_synthetic(fact)


@pytest.mark.parametrize("tag", sorted(TAGS))
def test_tag_omission_is_detected(tag):
    fact = synthetic_evidence()
    fact["tags"].remove(tag)
    with pytest.raises(AssertionError, match="complete tag set"):
        check_synthetic(fact)


@pytest.mark.parametrize("field", ["mentioned_at", "engineering_memory.started_at"])
def test_timestamp_omission_is_detected(field):
    fact = synthetic_evidence()
    del (fact if field == "mentioned_at" else fact["metadata"])[field]
    with pytest.raises(AssertionError, match=r"original .*timestamp|original temporal grounding"):
        check_synthetic(fact)


def test_decision_omission_is_detected():
    fact = synthetic_evidence()
    fact["text"] = "An unrelated synthetic fact."
    with pytest.raises(AssertionError, match="known engineering decision"):
        check_synthetic(fact)


def test_decoder_rejects_missing_version():
    fact = synthetic_evidence()
    del fact["metadata"]["engineering_memory.version"]
    with pytest.raises(MemoryStoreRejected):
        check_synthetic(fact)


def test_reimport_evidence_positive_control():
    assert_reimport_facts(
        [
            {"id": "fact-a", "document_id": "chatgpt:replay-a", "text": "Orchard cobalt relay."},
            {"id": "fact-b", "document_id": "chatgpt:replay-b", "text": "Orchard amber queue."},
        ],
        {"chatgpt:replay-a": "Orchard cobalt relay.", "chatgpt:replay-b": "Orchard amber queue."},
    )
    assert_replay_activity([], [], {"calls": 2, "errors": 0}, {"calls": 2, "errors": 0}, 0)


@pytest.mark.parametrize("corruption", ["missing", "extra", "duplicate", "stale"])
def test_reimport_recall_corruption_is_detected(corruption):
    facts = [
        {"id": "fact-a", "document_id": "chatgpt:replay-a", "text": "Orchard cobalt relay."},
        {"id": "fact-b", "document_id": "chatgpt:replay-b", "text": "Orchard amber queue."},
    ]
    expected = {
        "chatgpt:replay-a": "Orchard cobalt relay.",
        "chatgpt:replay-b": "Orchard amber queue.",
    }
    if corruption == "missing":
        facts.pop()
    elif corruption == "extra":
        facts.append({"id": "extra", "document_id": "unexpected", "text": "Orchard stray."})
    elif corruption == "duplicate":
        facts.append({**facts[0], "id": "duplicate"})
    else:
        expected["chatgpt:replay-a"] = "Orchard silver relay."
    with pytest.raises(AssertionError):
        assert_reimport_facts(facts, expected)


@pytest.mark.parametrize(
    "submitted,expected,calls,errors",
    [
        (["chatgpt:replay-a"], [], 0, 0),
        ([], [], 1, 0),
        (["chatgpt:replay-b"], ["chatgpt:replay-a"], 1, 0),
        ([], [], 0, 1),
    ],
)
def test_reimport_activity_corruption_is_detected(submitted, expected, calls, errors):
    with pytest.raises(AssertionError):
        assert_replay_activity(
            submitted,
            expected,
            {"calls": 2, "errors": 0},
            {"calls": 2 + calls, "errors": errors},
            len(expected),
        )


@live
def test_reimport_unchanged(engine, tmp_path):
    verify_reimport(engine, tmp_path, "unchanged")


@live
def test_reimport_state_loss(engine, tmp_path):
    verify_reimport(engine, tmp_path, "state-loss")


@live
def test_reimport_changed(engine, tmp_path):
    verify_reimport(engine, tmp_path, "changed")


def assert_reimport_facts(facts, expected):
    """Count documents from recall, with stronger one-fact fixture cardinality."""
    assert {fact["document_id"] for fact in facts} == set(expected), "recalled document identities"
    for document, decision in expected.items():
        matching = [fact for fact in facts if fact["document_id"] == document]
        assert len(matching) == 1, "one controlled fact per document"
        assert matching[0]["text"] == decision, "current controlled decision"


def assert_replay_activity(submitted, expected, before, after, extraction_delta):
    assert sorted(submitted) == sorted(expected), "submitted identities"
    assert after["errors"] == before["errors"] == 0, "extraction errors"
    if extraction_delta is not None:
        assert after["calls"] - before["calls"] == extraction_delta, "extraction calls"


REIMPORT_FACTS = {
    "chatgpt:replay-a": "Orchard cobalt relay isolates worker retries.",
    "chatgpt:replay-b": "Orchard amber queue preserves event ordering.",
}
REPLACEMENT = "Orchard silver relay isolates worker retries."


class RecordingStore:
    """Observe real submissions without replacing the memory implementation."""

    def __init__(self, memory):
        self.memory = memory
        self.submitted = []

    def retain(self, enriched):
        self.submitted.append(enriched.document_id)
        return self.memory.retain(enriched)


def fixture_stats():
    with httpx.Client(trust_env=False, timeout=10) as client:
        response = client.get(os.environ["CONTRACT_FIXTURE_URL"] + "/stats")
        response.raise_for_status()
        return response.json()


def recall_corpus(client, root, expected):
    # Recall is ranked, not an inventory API. This tiny scratch bank contains two
    # short, deterministic facts; query broadly and by every original/current fact.
    facts = {}
    for query in ["Orchard relay queue", *REIMPORT_FACTS.values(), *expected.values()]:
        response = client.post(
            root + "/memories/recall",
            json={"query": query, "types": ["world"], "budget": "high", "max_tokens": 32768},
        )
        response.raise_for_status()
        for fact in response.json()["results"]:
            facts[fact["id"]] = fact
    assert_reimport_facts(list(facts.values()), expected)
    return facts


def write_corpus(path, expected):
    records = [
        synth.linear_record(
            identity.removeprefix("chatgpt:"),
            synth.message("user", "Synthetic contract fact: " + decision),
            title="Synthetic Orchard replay",
            create_time=ORIGINAL.timestamp(),
            update_time=ORIGINAL.timestamp(),
        )
        for identity, decision in expected.items()
    ]
    synth.write_directory(path, records)
    return records


def import_corpus(tmp_path, settings, expected):
    # Fresh adapter lifetimes on every invocation rule out in-process retry keys
    # as the protection in the lost-state case.
    export = tmp_path / "export"
    records = write_corpus(export, expected)
    archive = LocalRawArchive(tmp_path / "archive")
    state = SQLiteImportState(tmp_path / "state.db")
    state.initialize()
    try:
        with HindsightStore(settings) as memory:
            recorder = RecordingStore(memory)
            pipeline = IngestionPipeline(
                sanitizer=PatternSecretSanitizer(),
                classifier=AliasProjectClassifier(
                    ProjectRuleSet(rules=(ProjectRule(project="orchard", aliases=("Orchard",)),))
                ),
                archive=archive,
                state=state,
                memory=recorder,
                importer_version="synthetic-reimport-v1",
                bank=settings.bank_id,
                repository="synthetic/orchard",
                user="synthetic",
            )
            report = pipeline.run(ChatGPTExportSource(export))
            assert report.failed == 0 and report.terminal_error is None, report
            for (identity, decision), record in zip(expected.items(), records, strict=True):
                assert json.loads(archive.load_original(identity).content) == record
                normalized = archive.load(identity)
                assert normalized.conversation.started_at == ORIGINAL
                assert decision in normalized.conversation.messages[0].text
            return report, recorder.submitted
    finally:
        state.close()


def verify_reimport(engine, tmp_path, scenario):
    settings, client, root = engine
    before = fixture_stats()
    baseline, submitted = import_corpus(tmp_path, settings, REIMPORT_FACTS)
    assert (baseline.imported, baseline.skipped) == (2, 0)
    assert_replay_activity(submitted, list(REIMPORT_FACTS), before, fixture_stats(), 2)
    original = recall_corpus(client, root, REIMPORT_FACTS)
    expected = dict(REIMPORT_FACTS)
    if scenario == "state-loss":
        # All state connections were disposed by import_corpus. Only this test's
        # DB is removed; preserve its archive and bank for actual recovery.
        (tmp_path / "state.db").unlink()
    elif scenario == "changed":
        expected["chatgpt:replay-a"] = REPLACEMENT
    before = fixture_stats()
    replay, submitted = import_corpus(tmp_path, settings, expected)
    after = fixture_stats()
    wanted = {"unchanged": [], "state-loss": list(expected), "changed": ["chatgpt:replay-a"]}
    assert_replay_activity(
        submitted,
        wanted[scenario],
        before,
        after,
        {"unchanged": 0, "state-loss": None, "changed": 1}[scenario],
    )
    assert (replay.imported, replay.skipped) == (len(wanted[scenario]), 2 - len(wanted[scenario]))
    recalled = recall_corpus(client, root, expected)
    if scenario == "unchanged":
        assert set(recalled) == set(original), "unchanged replay preserves fact identities"


@live
def test_import_to_access_tools(engine, tmp_path):
    """Real import + live memory recall through the consumer's stdio protocol."""
    import sys

    import anyio
    from mcp.client import Client
    from mcp.client.stdio import StdioServerParameters

    settings, _, _ = engine
    import_decision(tmp_path, settings)
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("ENGINEERING_MEMORY_")
    }
    environment.update(
        {
            "ENGINEERING_MEMORY_HINDSIGHT__BASE_URL": str(settings.base_url),
            "ENGINEERING_MEMORY_HINDSIGHT__BANK_ID": settings.bank_id,
            "ENGINEERING_MEMORY_ARCHIVE_ROOT": str(tmp_path / "archive"),
        }
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
                result = await client.call_tool(
                    "search_memory",
                    {
                        "query": "Orchard cobalt relay",
                        "tags": ["project:orchard", "source:chatgpt"],
                    },
                )
                assert not result.is_error, result
                matches = result.structured_content["results"]
                matching = [item for item in matches if item["document_id"] == DOCUMENT]
                assert matching and DECISION in matching[0]["content"]
                assert datetime.fromisoformat(matching[0]["started_at"]) == ORIGINAL
                for key, value in EXPECTED.items():
                    assert matching[0]["provenance"][key] == value
                page = await client.call_tool("get_conversation", {"document_id": DOCUMENT})
                assert not page.is_error
                assert DECISION in page.structured_content["messages"][0]["text"]
                excluded = await client.call_tool(
                    "search_memory",
                    {
                        "query": "Orchard cobalt relay",
                        "tags": ["project:another"],
                    },
                )
                assert not excluded.is_error and excluded.structured_content["results"] == []

    anyio.run(scenario)
