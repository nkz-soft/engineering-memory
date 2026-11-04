"""Real engine lifecycle and optional real-extractor synthesis; synthetic history only."""

import json
import os
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from engineering_memory.access.service import MemoryAccess
from engineering_memory.archive import OriginalPayload
from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.classification import AliasProjectClassifier, ProjectRule, ProjectRuleSet
from engineering_memory.ingestion.chatgpt import ChatGPTExportSource
from engineering_memory.ingestion.pipeline import IngestionPipeline
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.memory.hindsight.project_models import (
    HindsightProjectModels,
    model_definition,
)
from engineering_memory.memory.hindsight.provision import provision
from engineering_memory.memory.hindsight.store import HindsightStore
from engineering_memory.memory.interface.project_models import ModelKind, ProjectModelKey
from engineering_memory.sanitization import PatternSecretSanitizer
from engineering_memory.settings import HindsightSettings
from tests.contracts import conversations
from tests.synthetic import chatgpt_export as synth

pytestmark = pytest.mark.skipif(
    os.environ.get("ENGINEERING_MEMORY_LIVE_MODELS") != "1", reason="isolated model gate only"
)


def record_semantic_evidence(section, kind, value):
    """Optional explicit artifact for human semantic review; this corpus is synthetic."""
    location = os.environ.get("ENGINEERING_MEMORY_MODELS_EVIDENCE")
    if location:
        path = Path(location)
        evidence = json.loads(path.read_text()) if path.exists() else {}
        evidence.setdefault(section, {})[kind] = value
        path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


@pytest.fixture
def model_engine():
    url = os.environ["ENGINEERING_MEMORY_LIVE_STORE_URL"]
    settings = HindsightSettings(base_url=url, bank_id="synthetic-models-" + uuid4().hex)
    provision(settings)
    with httpx.Client(base_url=url, timeout=30, trust_env=False) as client:
        root = "/v1/default/banks/" + settings.bank_id
        try:
            yield settings, client, root
        finally:
            assert client.delete(root).status_code in {200, 204, 404}


def import_records(tmp_path, settings, rows):
    export = tmp_path / "export"
    synth.write_directory(
        export,
        [
            synth.linear_record(
                identity,
                synth.message("user", "Synthetic contract fact: " + text),
                title="Orchard synthetic history",
                create_time=timestamp,
                update_time=timestamp,
            )
            for identity, text, timestamp in rows
        ],
    )
    archive = LocalRawArchive(tmp_path / "archive")
    state = SQLiteImportState(tmp_path / "state.db")
    state.initialize()
    try:
        with HindsightStore(settings) as memory:
            pipeline = IngestionPipeline(
                archive=archive,
                state=state,
                memory=memory,
                sanitizer=PatternSecretSanitizer(),
                classifier=AliasProjectClassifier(
                    ProjectRuleSet(rules=(ProjectRule(project="orchard", aliases=("Orchard",)),))
                ),
                importer_version="synthetic-models-v1",
                bank=settings.bank_id,
            )
            report = pipeline.run(ChatGPTExportSource(export))
            assert report.failed == 0
            skipped = pipeline.run(ChatGPTExportSource(export))
            assert skipped.skipped == len(rows)
    finally:
        state.close()
    return archive


def test_models_import_refresh_read_and_scope(model_engine, tmp_path):
    settings, client, root = model_engine
    archive = import_records(
        tmp_path,
        settings,
        [
            ("architecture", "Orchard uses a cobalt relay to isolate worker retries.", 1577923200),
            (
                "gateway",
                "Orchard uses Python 3.13 with SQLite, and an amber gateway for request admission.",
                1609459200,
            ),
        ],
    )
    # Both lexical competitors must be excluded, including the untagged memory.
    with HindsightStore(settings) as store:
        for identity, project, text in [
            ("competitor", "beta", "Orchard uses a magenta broker."),
            ("untagged", "unknown", "Orchard uses a silver database."),
        ]:
            enriched = conversations.enrich(
                conversations.conversation(identity, text="Synthetic contract fact: " + text),
                project=project,
            )
            if identity == "untagged":
                enriched = enriched.model_copy(update={"tags": ()})
            archive.store(
                enriched, OriginalPayload(content=b"synthetic original", media_type="text/plain")
            )
            store.retain(enriched)
    with HindsightProjectModels(settings) as models, HindsightStore(settings) as store:
        access = MemoryAccess(store, archive, models=models)
        for kind in ModelKind:
            key = ProjectModelKey(project="orchard", kind=kind)
            assert models.get_project_model(key).status == "missing"
            outcome = models.refresh_project_model(key)
            assert outcome.status == "completed", outcome
            result = access.get_project_model(project="orchard", kind=kind.value)
            record_semantic_evidence("initial", kind.value, result)
            content = result["content"].lower()
            if kind == "architecture":
                assert "cobalt" in content and "amber" in content
            assert "magenta" not in content and "silver" not in content
            assert result["supports"]
            for support in result["supports"]:
                assert support["document_id"] in {"chatgpt:architecture", "chatgpt:gateway"}
                access.get_conversation(document_id=support["document_id"])
        assert (
            models.refresh_project_model(
                ProjectModelKey(project="orchard", kind="architecture")
            ).status
            == "completed"
        )
        listing = client.get(root + "/mental-models").json()
        assert len(listing["items"]) == 3

        import_records(
            tmp_path,
            settings,
            [
                (
                    "replacement",
                    "Orchard now uses a jade relay instead of the cobalt relay, "
                    "and PostgreSQL instead of SQLite. This supersedes the earlier decisions.",
                    1640995200,
                )
            ],
        )
        for kind in ModelKind:
            key = ProjectModelKey(project="orchard", kind=kind)
            assert models.refresh_project_model(key).status == "completed"
            refreshed = access.get_project_model(project="orchard", kind=kind.value)
            record_semantic_evidence("refreshed", kind.value, refreshed)
            expected = "postgresql" if kind == "stack" else "jade"
            assert expected in refreshed["content"].lower()
            assert "chatgpt:replacement" in {
                support["document_id"] for support in refreshed["supports"]
            }


def test_models_keep_unresolved_decisions_visible(model_engine, tmp_path):
    settings, _, _ = model_engine
    archive = import_records(
        tmp_path,
        settings,
        [
            (
                "proposals",
                "Orchard has unresolved competing proposals for Rust and Go. "
                "Neither has been accepted.",
                1577923200,
            )
        ],
    )
    with HindsightProjectModels(settings) as models, HindsightStore(settings) as memory:
        key = ProjectModelKey(project="orchard", kind="decisions")
        assert models.refresh_project_model(key).status == "completed"
        result = MemoryAccess(memory, archive, models=models).get_project_model(
            project="orchard", kind="decisions"
        )
        content = result["content"].lower()
        record_semantic_evidence("unresolved", "decisions", result)
        assert any(
            term in content for term in ("unresolved", "proposal", "not accepted", "not settled")
        )
        assert "python" not in content and "postgresql" not in content
        assert {support["document_id"] for support in result["supports"]} == {"chatgpt:proposals"}


def test_models_failed_refresh_preserves_last_good(model_engine, tmp_path):
    settings, client, root = model_engine
    import_records(tmp_path, settings, [("decision", "Orchard uses an amber gateway.", 1577923200)])
    key = ProjectModelKey(project="orchard", kind="stack")
    with HindsightProjectModels(settings) as models:
        assert models.refresh_project_model(key).status == "completed"
        previous = models.get_project_model(key)
        identity = model_definition(key)["id"]
        original = client.get(root + "/mental-models/" + identity).json()
        path = root + "/mental-models/" + identity
        client.patch(path, json={"source_query": "FORCE_FIXTURE_FAILURE"}).raise_for_status()
        try:
            submitted = client.post(path + "/refresh", json={"mode": "full"}).json()
            operation = submitted["operation_id"]
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                status = client.get(root + "/operations/" + operation).json()["status"]
                if status in {"completed", "failed", "cancelled"}:
                    break
                time.sleep(0.2)
            assert status == "failed"
        finally:
            client.patch(path, json={"source_query": original["source_query"]}).raise_for_status()
        after = models.get_project_model(key)
        assert after.snapshot.content == previous.snapshot.content
        assert after.snapshot.refreshed_at == previous.snapshot.refreshed_at
        assert after.snapshot.last_refresh_failed_at is not None
