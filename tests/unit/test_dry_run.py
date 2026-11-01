"""Preview decisions must not produce durable side effects or leak conversation text."""

import pytest

from engineering_memory.ingestion.pipeline import IngestionPipeline
from engineering_memory.ingestion.state import ImportRecord, ImportStatus
from tests.contracts.conversations import IMPORTED_AT, as_read, conversation
from tests.fakes.classifier import InMemoryProjectClassifier
from tests.fakes.sanitizer import InMemorySecretSanitizer
from tests.fakes.source import InMemoryConversationSource
from tests.fakes.state import InMemoryImportState


class Forbidden:
    def __getattr__(self, name):
        raise AssertionError(f"forbidden side effect: {name}")


def pipeline(state=None, sanitizer=None):
    return IngestionPipeline(
        sanitizer=sanitizer or InMemorySecretSanitizer(),
        classifier=InMemoryProjectClassifier({"wolverine": "wolverine"}),
        archive=Forbidden(),
        memory=Forbidden(),
        state=state or InMemoryImportState(),
        importer_version="test",
        clock=lambda: IMPORTED_AT,
    )


def test_preview_metadata_and_repeated_identity_without_writes():
    item = as_read(conversation(text="Wolverine hunter2"))[0]
    state = InMemoryImportState()
    report = pipeline(state).run(InMemoryConversationSource((item, item)), dry_run=True)
    assert (report.imported, report.skipped) == (1, 1)
    assert state.records == ()
    row = report.outcomes[0]
    assert row.document_id == "chatgpt:abc123"
    assert row.project == "project:wolverine"
    assert row.timestamp == item.conversation.started_at
    assert row.redaction_categories == ("password",)
    assert report.outcomes[1].project == "project:wolverine"
    assert "hunter2" not in report.model_dump_json()


@pytest.mark.parametrize(
    "force, expected", [(False, ImportStatus.SKIPPED), (True, ImportStatus.IMPORTED)]
)
def test_preview_existing_state_and_force(force, expected):
    item = as_read(conversation())[0]
    state = InMemoryImportState()
    state.record(
        ImportRecord(
            source=item.conversation.source,
            source_id="abc123",
            document_id="chatgpt:abc123",
            content_hash=item.conversation.content_hash(),
            recorded_at=IMPORTED_AT,
            status=ImportStatus.IMPORTED,
        )
    )
    before = state.records
    report = pipeline(state).run(InMemoryConversationSource((item,)), dry_run=True, force=force)
    assert report.outcomes[0].status == expected
    assert report.outcomes[0].project == "project:wolverine"
    assert state.records == before


def test_preview_preparation_failure_is_not_recorded():
    item = as_read(conversation())[0]
    state = InMemoryImportState()
    report = pipeline(state, InMemorySecretSanitizer(fails=True)).run(
        InMemoryConversationSource((item,)), dry_run=True
    )
    assert report.failed == 1
    assert report.outcomes[0].error.value == "sanitize"
    assert state.records == ()


@pytest.mark.parametrize("adapter", ["memory", "state"])
def test_real_run_rejects_missing_adapter_before_side_effects(adapter):
    runner = pipeline()
    setattr(runner, adapter, None)
    with pytest.raises(ValueError, match="requires memory and state"):
        runner.run(InMemoryConversationSource(as_read(conversation())))


def test_mixed_sequential_preview_matches_actual_import():
    from tests.fakes.archive import InMemoryRawArchive
    from tests.fakes.store import InMemoryMemoryStore

    first = conversation(text="first Wolverine revision")
    changed = conversation(text="changed Wolverine revision")
    other = conversation("other")
    items = as_read(first, first, changed, changed, other)
    preview = pipeline().run(InMemoryConversationSource(items), dry_run=True)
    runner = pipeline()
    runner.archive = InMemoryRawArchive()
    runner.memory = InMemoryMemoryStore()
    real = runner.run(InMemoryConversationSource(items))
    expected = [
        ImportStatus.IMPORTED,
        ImportStatus.SKIPPED,
        ImportStatus.IMPORTED,
        ImportStatus.SKIPPED,
        ImportStatus.IMPORTED,
    ]
    assert [row.status for row in preview.outcomes] == expected
    assert [row.status for row in real.outcomes] == expected
    assert (preview.imported, preview.skipped) == (3, 2)


def test_failed_skip_metadata_does_not_change_next_skip():
    item = as_read(conversation())[0]
    state = InMemoryImportState()
    state.record(
        ImportRecord(
            source=item.conversation.source,
            source_id="abc123",
            document_id="chatgpt:abc123",
            content_hash=item.conversation.content_hash(),
            recorded_at=IMPORTED_AT,
            status=ImportStatus.IMPORTED,
        )
    )
    before = state.records

    class FailOnce(InMemorySecretSanitizer):
        calls = 0

        def sanitize(self, conversation):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("PRIVATE-CANARY")
            return super().sanitize(conversation)

    report = pipeline(state, FailOnce()).run(InMemoryConversationSource((item, item)), dry_run=True)
    assert [row.status for row in report.outcomes] == [ImportStatus.FAILED, ImportStatus.SKIPPED]
    assert state.records == before
    assert "PRIVATE-CANARY" not in report.model_dump_json()


def test_preview_operation_log_marks_projected_action():
    from structlog.testing import capture_logs

    with capture_logs() as events:
        pipeline().run(InMemoryConversationSource(as_read(conversation())), dry_run=True)
    operation = next(event for event in events if event["event"] == "ingestion.operation")
    assert operation["status"] == "would_import"
    assert operation["dry_run"] is True
