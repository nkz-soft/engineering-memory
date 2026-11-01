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
