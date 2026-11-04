"""Model reads verify archive identity before returning generated evidence."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from engineering_memory.access.service import AccessError, MemoryAccess
from engineering_memory.archive import OriginalPayload
from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.memory.interface.project_models import (
    ModelSupport,
    ProjectModelKey,
    ProjectModelRead,
    ProjectModelSnapshot,
)
from tests.contracts import conversations as synth


def setup_access(tmp_path):
    enriched = synth.enrich(
        synth.conversation("support", text="Sanitized alpha evidence"), project="alpha"
    )
    archive = LocalRawArchive(tmp_path / "archive")
    archive.store(enriched, OriginalPayload(content=b"ORIGINAL_SECRET", media_type="text/plain"))
    reader = Mock()
    key = ProjectModelKey(project="alpha", kind="architecture")
    reader.get_project_model.return_value = ProjectModelRead(
        key=key,
        status="ready",
        snapshot=ProjectModelSnapshot(
            content="Architecture summary",
            refreshed_at=datetime(2026, 11, 4, tzinfo=UTC),
            stale=True,
            supports=(
                ModelSupport(document_id=enriched.document_id, provenance=enriched.provenance),
            ),
        ),
    )
    return MemoryAccess(Mock(), archive, models=reader), reader, archive, enriched


def test_model_read_returns_support_original_time_and_staleness(tmp_path):
    access, _, _, enriched = setup_access(tmp_path)
    result = access.get_project_model(project="alpha", kind="architecture")
    assert result["content"] == "Architecture summary" and result["stale"] is True
    assert result["supports"][0]["document_id"] == "chatgpt:support"
    assert result["supports"][0][
        "started_at"
    ] == enriched.conversation.started_at.isoformat().replace("+00:00", "Z")
    assert "ORIGINAL_SECRET" not in str(result)


@pytest.mark.parametrize(
    "arguments",
    [
        {"project": "", "kind": "stack"},
        {"project": "unknown", "kind": "stack"},
        {"project": "alpha", "kind": "other"},
        {"project": 7, "kind": "stack"},
        {"project": "alpha", "kind": "stack", "refresh": True},
    ],
)
def test_invalid_model_read_does_not_contact_boundary(tmp_path, arguments):
    access, reader, _, _ = setup_access(tmp_path)
    with pytest.raises(AccessError, match="invalid_input"):
        access.get_project_model(**arguments)
    reader.get_project_model.assert_not_called()


@pytest.mark.parametrize("mismatch", ["project", "provenance", "missing", "empty_support"])
def test_model_archive_mismatch_fails_closed(tmp_path, mismatch):
    access, reader, _archive, enriched = setup_access(tmp_path)
    if mismatch == "empty_support":
        value = reader.get_project_model.return_value
        reader.get_project_model.return_value = value.model_copy(
            update={"snapshot": value.snapshot.model_copy(update={"supports": ()})}
        )
    elif mismatch == "missing":
        access.archive = LocalRawArchive(tmp_path / "missing")
    else:
        changed = enriched.provenance.model_copy(
            update={mismatch if mismatch == "project" else "importer_version": "beta"}
        )
        access.archive = Mock()
        access.archive.load.return_value = (
            synth.enrich(enriched.conversation, project="beta")
            if mismatch == "project"
            else enriched.model_copy(update={"provenance": changed})
        )
    with pytest.raises(AccessError):
        access.get_project_model(project="alpha", kind="architecture")


def test_missing_model_is_explicit_without_writes(tmp_path):
    access, reader, _, _ = setup_access(tmp_path)
    reader.get_project_model.return_value = ProjectModelRead(
        key=ProjectModelKey(project="alpha", kind="stack"), status="missing"
    )
    assert access.get_project_model(project="alpha", kind="stack") == {
        "project": "alpha",
        "kind": "stack",
        "status": "missing",
    }
    reader.refresh_project_model.assert_not_called()
