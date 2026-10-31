"""Production pipeline over real source, sanitizer, classifier, archive and state."""

from datetime import UTC, datetime

from structlog.testing import capture_logs

from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.classification import AliasProjectClassifier, ProjectRuleSet
from engineering_memory.ingestion.chatgpt import ChatGPTExportSource
from engineering_memory.ingestion.chatgpt.archive_source import ChatGPTArchiveSource
from engineering_memory.ingestion.pipeline import IngestionPipeline
from engineering_memory.ingestion.report import RunStatus
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.ingestion.state import ImportStatus
from engineering_memory.normalization import Source
from engineering_memory.sanitization import PatternSecretSanitizer
from tests.fakes.store import InMemoryMemoryStore
from tests.synthetic import chatgpt_export as synth

NOW = datetime(2026, 10, 31, tzinfo=UTC)


def setup_pipeline(tmp_path):
    archive = LocalRawArchive(tmp_path / "archive")
    state = SQLiteImportState(tmp_path / "state.db")
    state.initialize()

    class CheckedMemory(InMemoryMemoryStore):
        calls = 0

        def retain(self, enriched):
            assert archive.load(enriched.document_id) == enriched
            assert archive.load_original(enriched.document_id).content
            self.calls += 1
            super().retain(enriched)

    memory = CheckedMemory()
    pipeline = IngestionPipeline(
        sanitizer=PatternSecretSanitizer(),
        classifier=AliasProjectClassifier(ProjectRuleSet()),
        archive=archive,
        state=state,
        memory=memory,
        importer_version="test",
        clock=lambda: NOW,
    )
    return pipeline, archive, state, memory


def records():
    return [
        synth.linear_record("one", synth.message("user", "password=hunter2")),
        synth.linear_record("two", synth.message("user", "a safe fact")),
    ]


def test_unchanged_skip_uses_raw_hash_and_never_replaces_success(tmp_path, monkeypatch):
    pipeline, archive, state, memory = setup_pipeline(tmp_path)
    path = tmp_path / "export"
    synth.write_directory(path, records())
    source = ChatGPTExportSource(path)
    assert pipeline.run(source).imported == 2
    before = state.find(Source.CHATGPT, "one")

    def must_not_call(*args):
        raise AssertionError("unchanged item reached a downstream boundary")

    for adapter, method in [
        (pipeline.sanitizer, "sanitize"),
        (pipeline.classifier, "classify"),
        (archive, "store"),
        (memory, "retain"),
        (state, "record"),
    ]:
        monkeypatch.setattr(adapter, method, must_not_call)
    second = pipeline.run(source)
    assert (second.imported, second.skipped, second.failed) == (0, 2, 0)
    assert second.status == RunStatus.SUCCESS
    assert state.find(Source.CHATGPT, "one") == before
    assert memory.calls == 2


def test_changed_and_forced_imports_reuse_identity_and_archive_replay(tmp_path):
    pipeline, archive, _state, memory = setup_pipeline(tmp_path)
    path = tmp_path / "export"
    synth.write_directory(path, records())
    source = ChatGPTExportSource(path)
    assert pipeline.run(source).imported == 2
    changed = records()
    changed[1] = synth.linear_record("two", synth.message("user", "a changed fact"))
    synth.write_directory(path, changed)
    result = pipeline.run(source)
    assert (result.imported, result.skipped, result.failed) == (1, 1, 0)
    assert memory.recall("changed fact")
    assert len(memory.retained) == 2
    originals = {i: archive.load_original(i) for i in memory.retained}
    replayed = pipeline.run(ChatGPTArchiveSource(archive), force=True)
    assert (replayed.imported, replayed.skipped) == (2, 0)
    assert {i: archive.load_original(i) for i in memory.retained} == originals
    assert memory.calls == 5


def test_real_import_redacts_all_served_forms_and_preserves_original(tmp_path):
    pipeline, archive, state, memory = setup_pipeline(tmp_path)
    path = tmp_path / "export"
    synth.write_directory(path, records())
    source = ChatGPTExportSource(path)
    read = next(source.read())
    with capture_logs() as logs:
        report = pipeline.run(source)
    enriched = archive.load("chatgpt:one")
    assert report.imported == 2
    assert enriched.conversation.started_at == read.conversation.started_at
    assert enriched.provenance.imported_at == NOW
    assert enriched.provenance.project == "unknown"
    assert "hunter2" not in enriched.model_dump_json() + str(logs) + report.model_dump_json()
    assert not memory.recall("hunter2")
    assert archive.load_original("chatgpt:one") == read.original
    assert b"hunter2" in read.original.content
    assert state.find(Source.CHATGPT, "one").content_hash == read.conversation.content_hash()


def test_failed_import_is_retried_with_real_durable_state(tmp_path, monkeypatch):
    pipeline, _archive, state, memory = setup_pipeline(tmp_path)
    path = tmp_path / "export"
    synth.write_directory(path, records())
    retain = memory.retain

    def fail_one(enriched):
        if enriched.document_id == "chatgpt:one":
            raise RuntimeError("private failure text")
        retain(enriched)

    monkeypatch.setattr(memory, "retain", fail_one)
    assert pipeline.run(ChatGPTExportSource(path)).failed == 1
    assert state.find(Source.CHATGPT, "one").status == ImportStatus.FAILED
    monkeypatch.setattr(memory, "retain", retain)
    result = pipeline.run(ChatGPTExportSource(path))
    assert (result.imported, result.skipped, result.failed) == (1, 1, 0)
    assert state.find(Source.CHATGPT, "one").status == ImportStatus.IMPORTED


def test_real_malformed_middle_record_imports_neighbors(tmp_path):
    pipeline, _archive, state, memory = setup_pipeline(tmp_path)
    path = tmp_path / "export"
    export = [
        synth.linear_record(i, synth.message("user", "safe fact"))
        for i in ("first", "broken", "last")
    ]
    export[1]["mapping"]["n1"]["parent"] = "missing-parent"
    synth.write_directory(path, export)
    result = pipeline.run(ChatGPTExportSource(path))
    assert (result.imported, result.failed) == (2, 1)
    assert result.status == RunStatus.PARTIAL_SUCCESS
    assert result.outcomes[1].source_id == "broken"
    assert result.outcomes[1].completed_at == NOW
    assert memory.retained == ("chatgpt:first", "chatgpt:last")
    assert state.find(Source.CHATGPT, "broken") is None


def test_unusable_parser_identity_does_not_abort_later_conversations(tmp_path):
    pipeline, _archive, _state, memory = setup_pipeline(tmp_path)
    path = tmp_path / "export"
    broken = synth.linear_record("bad id", synth.message("user", "broken identity"))
    synth.write_directory(
        path, [broken, synth.linear_record("last", synth.message("user", "safe"))]
    )
    result = pipeline.run(ChatGPTExportSource(path))
    assert (result.failed, result.imported) == (1, 1)
    assert result.outcomes[0].source_id is None
    assert memory.retained == ("chatgpt:last",)


def test_retain_succeeded_but_state_write_failed_can_resume_safely(tmp_path, monkeypatch):
    pipeline, _archive, state, memory = setup_pipeline(tmp_path)
    path = tmp_path / "export"
    synth.write_directory(path, records())
    record = state.record

    def fail_success(value):
        if value.source_id == "one" and value.status == ImportStatus.IMPORTED:
            raise OSError("synthetic private error")
        record(value)

    monkeypatch.setattr(state, "record", fail_success)
    first = pipeline.run(ChatGPTExportSource(path))
    assert (first.imported, first.failed) == (1, 1)
    assert len(memory.retained) == 2
    assert state.find(Source.CHATGPT, "one").status == ImportStatus.FAILED
    monkeypatch.setattr(state, "record", record)
    second = pipeline.run(ChatGPTExportSource(path))
    assert (second.imported, second.skipped, second.failed) == (1, 1, 0)
    assert memory.calls == 3 and len(memory.retained) == 2
