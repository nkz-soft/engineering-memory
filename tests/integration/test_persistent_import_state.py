"""Issue #14: persistent skip/retry/force and ADR-006 retention acceptance."""

import re
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.ingestion import ImportStateUnavailable, ImportStatus
from engineering_memory.ingestion.chatgpt import ChatGPTExportSource
from engineering_memory.ingestion.chatgpt.archive_source import ChatGPTArchiveSource
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.memory.interface import MemoryStoreUnavailable
from engineering_memory.normalization import Source
from engineering_memory.sanitization import PatternSecretSanitizer, RedactionCategory
from engineering_memory.sanitization.patterns import PATTERNS, Pattern
from tests.contracts.conversations import conversation
from tests.fakes.classifier import InMemoryProjectClassifier
from tests.fakes.store import InMemoryMemoryStore
from tests.integration.pipeline import Pipeline
from tests.synthetic import chatgpt_export as synth

NOW = datetime(2026, 10, 27, tzinfo=UTC)


class CountedStore(InMemoryMemoryStore):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.fail_ids = set()

    def retain(self, enriched):
        self.calls.append(enriched.document_id)
        if enriched.document_id in self.fail_ids:
            raise MemoryStoreUnavailable("synthetic memory failure")
        super().retain(enriched)


def export_to(path, *items):
    path.write_text(
        "[" + ",".join(synth.serialize(synth.from_conversation(c)) for c in items) + "]"
    )


@pytest.fixture
def setup(tmp_path):
    export = tmp_path / "export.json"
    state = SQLiteImportState(tmp_path / "state.db")
    state.initialize()
    archive = LocalRawArchive(tmp_path / "archive")
    memory = CountedStore()
    pipeline = Pipeline(
        ChatGPTExportSource(export),
        PatternSecretSanitizer(),
        InMemoryProjectClassifier(),
        archive,
        memory,
        state,
    )
    yield export, pipeline
    state.close()


def reopen(pipeline):
    pipeline.state.close()
    state = SQLiteImportState(pipeline.state.path)
    state.validate()
    return replace(pipeline, state=state)


def test_reopened_refreshes_skip_without_overwriting_success(setup):
    export, pipeline = setup
    export_to(export, conversation(text="Wolverine password=hunter2"))
    assert pipeline.run(now=NOW).imported == ["abc123"]
    remembered = pipeline.state.find(Source.CHATGPT, "abc123")
    assert not pipeline.store.recall("hunter2")
    for _ in range(3):
        pipeline = reopen(pipeline)
        assert pipeline.run(now=NOW).skipped == ["abc123"]
        assert pipeline.state.find(Source.CHATGPT, "abc123") == remembered
    assert pipeline.store.calls == ["chatgpt:abc123"]


def test_one_character_change_reimports_but_title_and_version_do_not(setup):
    export, pipeline = setup
    export_to(export, conversation(text="value A"))
    pipeline.run(now=NOW)
    export_to(export, conversation(text="value A", title="Renamed"))
    assert replace(pipeline, importer_version="new").run(now=NOW).skipped == ["abc123"]
    export_to(export, conversation(text="value B"))
    assert pipeline.run(now=NOW).imported == ["abc123"]
    assert pipeline.store.calls == ["chatgpt:abc123", "chatgpt:abc123"]
    assert pipeline.store.retained == ("chatgpt:abc123",)


def test_failure_persists_retries_and_does_not_abort_next_conversation(setup):
    export, pipeline = setup
    export_to(export, conversation("bad"), conversation("good"))
    pipeline.store.fail_ids.add("chatgpt:bad")
    first = pipeline.run(now=NOW)
    assert first.imported == ["good"]
    assert [f.source_id for f in first.failed] == ["bad"]
    pipeline = reopen(pipeline)
    failed = pipeline.state.find(Source.CHATGPT, "bad")
    assert failed.status is ImportStatus.FAILED and failed.error and failed.recorded_at == NOW
    pipeline.store.fail_ids.clear()
    assert pipeline.run(now=NOW).imported == ["bad"]
    assert pipeline.run(now=NOW).skipped == ["bad", "good"]
    assert pipeline.store.calls == ["chatgpt:bad", "chatgpt:good", "chatgpt:bad"]


def test_force_replays_archived_originals_under_changed_sanitization(setup):
    export, pipeline = setup
    export_to(export, conversation(text="Wolverine newly-private-marker password=hunter2"))
    pipeline.run(now=NOW)
    original = pipeline.archive.load_original("chatgpt:abc123")
    export.unlink()
    sanitizer = PatternSecretSanitizer(
        patterns=(
            *PATTERNS,
            Pattern(
                category=RedactionCategory.PASSWORD, expression=re.compile("newly-private-marker")
            ),
        )
    )
    pipeline = replace(
        reopen(pipeline), source=ChatGPTArchiveSource(pipeline.archive), sanitizer=sanitizer
    )
    assert pipeline.run(now=NOW).skipped == ["abc123"]
    assert pipeline.store.recall("newly-private-marker")
    assert pipeline.run(now=NOW, force=True).imported == ["abc123"]
    assert pipeline.store.calls == ["chatgpt:abc123", "chatgpt:abc123"]
    assert not pipeline.store.recall("newly-private-marker")
    assert not pipeline.store.recall("hunter2")
    assert pipeline.archive.load_original("chatgpt:abc123") == original


def test_failed_force_is_retried_by_ordinary_refresh(setup):
    export, pipeline = setup
    export_to(export, conversation())
    pipeline.run(now=NOW)
    pipeline.store.fail_ids.add("chatgpt:abc123")
    assert len(pipeline.run(now=NOW, force=True).failed) == 1
    pipeline.store.fail_ids.clear()
    assert pipeline.run(now=NOW).imported == ["abc123"]


def test_missing_and_empty_exports_preserve_state_archive_and_memory(setup):
    export, pipeline = setup
    export_to(export, conversation("one"), conversation("two"))
    pipeline.run(now=NOW)
    remembered = pipeline.state.find(Source.CHATGPT, "two")
    archived = pipeline.archive.load("chatgpt:two")
    original = pipeline.archive.load_original("chatgpt:two")
    for items in ((conversation("one"),), ()):
        export_to(export, *items)
        result = pipeline.run(now=NOW)
        assert not result.failed and not result.imported
        assert pipeline.state.find(Source.CHATGPT, "two") == remembered
        assert pipeline.archive.load("chatgpt:two") == archived
        assert pipeline.archive.load_original("chatgpt:two") == original
        assert set(pipeline.store.retained) == {"chatgpt:one", "chatgpt:two"}
    assert pipeline.store.calls == ["chatgpt:one", "chatgpt:two"]


@pytest.mark.parametrize("force", [False, True])
def test_lookup_failure_never_reaches_memory(setup, force):
    export, pipeline = setup
    export_to(export, conversation())
    pipeline.state.path.unlink()
    result = pipeline.run(now=NOW, force=force)
    assert len(result.failed) == 1
    assert pipeline.store.calls == []


def test_state_write_failure_after_retain_is_reported_and_resends(setup, monkeypatch):
    export, pipeline = setup
    export_to(export, conversation())
    real_record = pipeline.state.record

    def fail_record(record):
        raise ImportStateUnavailable("synthetic state failure")

    monkeypatch.setattr(pipeline.state, "record", fail_record)
    result = pipeline.run(now=NOW)
    assert len(result.failed) == 1 and not result.imported
    assert pipeline.store.calls == ["chatgpt:abc123"]
    monkeypatch.setattr(pipeline.state, "record", real_record)
    assert pipeline.run(now=NOW).imported == ["abc123"]
    assert pipeline.store.calls == ["chatgpt:abc123", "chatgpt:abc123"]
    assert pipeline.store.retained == ("chatgpt:abc123",)
