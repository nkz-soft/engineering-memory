"""Published catalog access stays scoped and preserves evidence guards."""

from unittest.mock import Mock

import pytest

from engineering_memory.access.service import AccessError, MemoryAccess
from engineering_memory.archive import OriginalPayload
from engineering_memory.archive.local import LocalRawArchive
from tests.contracts import conversations as fixtures


def test_published_catalog_scope_paging_and_guard(tmp_path):
    from engineering_memory.playbooks.service import PlaybookOperator
    from engineering_memory.playbooks.sqlite import SQLitePlaybookCatalog

    archive = LocalRawArchive(tmp_path / "archive")
    store = SQLitePlaybookCatalog(tmp_path / "playbooks.sqlite3")
    access = MemoryAccess(Mock(), archive, playbooks=store)
    assert access.list_project_playbooks(project="orchard") == {"items": [], "next_after_id": None}
    assert not store.path.exists()

    record = fixtures.enrich(fixtures.conversation_using_every_field(), project="orchard")
    archive.store(record, OriginalPayload(content=b"RAW_SENTINEL", media_type="text/plain"))
    operator = PlaybookOperator(store, archive)
    for slug in ("one", "two"):
        pending = operator.stage(
            "orchard", slug, {"title": slug, "steps": ["First"], "examples": [record.document_id]}
        )
        with pytest.raises(AccessError, match="not_found"):
            access.get_project_playbook(project="orchard", id=slug)
        operator.approve("orchard", slug, pending.revision)

    first = access.list_project_playbooks(project="orchard", limit=1)
    assert first == {"items": [{"id": "one", "title": "one", "version": 1}], "next_after_id": "one"}
    last = access.list_project_playbooks(project="orchard", after_id="one", limit=1)
    assert last == {"items": [{"id": "two", "title": "two", "version": 1}], "next_after_id": None}
    with pytest.raises(AccessError, match="not_found"):
        access.get_project_playbook(project="other", id="one")

    detail = access.get_project_playbook(project="orchard", id="one", version=1)
    assert detail["steps"] == ["First"]
    source = detail["examples"][0]
    guard = {key: source[key] for key in ("document_id", "project", "snapshot")}
    approved_record = access.get_conversation(**guard)
    assert approved_record["document_id"] == record.document_id
    assert "RAW_SENTINEL" not in str(approved_record)
    with pytest.raises(AccessError, match="not_found"):
        access.get_conversation(**(guard | {"snapshot": "0" * 64}))
    with pytest.raises(AccessError, match="invalid_input"):
        access.get_conversation(document_id=record.document_id, project="orchard")


def test_incompatible_catalog_is_unavailable(tmp_path):
    from engineering_memory.playbooks.sqlite import SQLitePlaybookCatalog

    catalog_file = tmp_path / "catalog.sqlite3"
    catalog_file.write_bytes(b"not a catalog" * 100)
    access = MemoryAccess(Mock(), Mock(), playbooks=SQLitePlaybookCatalog(catalog_file))
    with pytest.raises(AccessError, match="unavailable"):
        access.list_project_playbooks(project="orchard")
