"""Publication must preserve exact draft content and archived evidence."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from engineering_memory.archive import OriginalPayload
from engineering_memory.archive.local import LocalRawArchive
from tests.contracts import conversations as fixture

PROJECT = "orchard"
BOOK = "release"
EXAMPLE = fixture.conversation_using_every_field()


@pytest.fixture
def catalog(tmp_path):
    from engineering_memory.playbooks.service import PlaybookOperator
    from engineering_memory.playbooks.sqlite import SQLitePlaybookCatalog

    archive = LocalRawArchive(tmp_path / "archive")
    record = fixture.enrich(EXAMPLE, project=PROJECT)
    archive.store(record, OriginalPayload(content=b"private", media_type="text/plain"))
    store = SQLitePlaybookCatalog(tmp_path / "catalog.sqlite3")
    return archive, store, PlaybookOperator(store, archive), record


def draft(record, *steps):
    return {"title": "Release procedure", "steps": list(steps), "examples": [record.document_id]}


def test_publication_preserves_approved_versions_and_excludes_replacements(catalog):
    archive, store, operator, record = catalog
    next_example = fixture.enrich(
        EXAMPLE.model_copy(update={"source_id": "second-source"}), project=PROJECT
    )
    archive.store(next_example, OriginalPayload(content=b"second example", media_type="text/plain"))
    assert store.list_approved(PROJECT, None, 20) == []
    first = operator.stage(PROJECT, BOOK, draft(record, "Run tests", "Review notes"))
    assert operator.review(PROJECT, BOOK) == first
    assert store.get_approved(PROJECT, BOOK, None) is None
    assert operator.approve(PROJECT, BOOK, first.revision) == 1

    pending = operator.stage(PROJECT, BOOK, draft(record, "Unreviewed update"))
    second = operator.stage(PROJECT, BOOK, draft(next_example, "Review notes", "Run tests"))
    with pytest.raises(ValueError, match="draft_changed"):
        operator.approve(PROJECT, BOOK, pending.revision)
    assert store.get_approved(PROJECT, BOOK, None).content.steps == ["Run tests", "Review notes"]
    assert operator.approve(PROJECT, BOOK, second.revision) == 2
    assert operator.approve(PROJECT, BOOK, first.revision) == 1
    old = store.get_approved(PROJECT, BOOK, 1)
    new = store.get_approved(PROJECT, BOOK, None)
    assert old.content.steps == ["Run tests", "Review notes"]
    assert new.content.steps == ["Review notes", "Run tests"]
    assert old.content.examples == first.content.examples
    assert new.content.examples == second.content.examples
    assert old.content.examples[0].document_id != new.content.examples[0].document_id
    assert new.version == new.latest_version == 2
    assert store.get_approved("different", BOOK, 1) is None


def test_scope_source_drift_and_invalid_input_leave_pending_draft_intact(catalog):
    archive, store, operator, record = catalog
    with pytest.raises(ValueError, match="example_unavailable"):
        operator.stage("different", BOOK, draft(record, "Run tests"))
    pending = operator.stage(PROJECT, BOOK, draft(record, "Run tests"))
    with pytest.raises(ValueError, match="invalid_input"):
        operator.stage(PROJECT, BOOK, draft(record, " "))
    message = EXAMPLE.messages[0].model_copy(update={"text": "Changed archive message"})
    changed = EXAMPLE.model_copy(update={"messages": (message, *EXAMPLE.messages[1:])})
    archive.store(
        fixture.enrich(changed, project=PROJECT),
        OriginalPayload(content=b"changed", media_type="text/plain"),
    )
    with pytest.raises(ValueError, match="example_unavailable"):
        operator.approve(PROJECT, BOOK, pending.revision)
    assert operator.review(PROJECT, BOOK) == pending
    assert store.get_approved(PROJECT, BOOK, None) is None


def test_concurrent_approval_is_idempotent_and_text_is_sanitized(catalog):
    _, store, operator, record = catalog
    credential = "AKIA" + "ABCDEFGHIJKLMNOP"
    staged = operator.stage(PROJECT, BOOK, draft(record, f"Remove {credential}"))
    assert credential not in staged.content.steps[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        versions = list(
            pool.map(lambda _: operator.approve(PROJECT, BOOK, staged.revision), range(2))
        )
    assert versions == [1, 1]
    assert store.get_approved(PROJECT, BOOK, 2) is None


def test_approval_rolls_back_if_the_draft_cannot_be_cleared(catalog):
    import sqlite3

    _, store, operator, record = catalog
    staged = operator.stage(PROJECT, BOOK, draft(record, "Run tests"))
    with sqlite3.connect(store.path) as connection:
        connection.execute("""
            CREATE TRIGGER block_draft_removal BEFORE DELETE ON drafts
            BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END
        """)
    with pytest.raises(ValueError, match="catalog_unavailable"):
        operator.approve(PROJECT, BOOK, staged.revision)
    assert operator.review(PROJECT, BOOK) == staged
    assert store.get_approved(PROJECT, BOOK, None) is None
