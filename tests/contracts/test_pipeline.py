"""Observable ordering, isolation and privacy at the pipeline boundaries."""

from datetime import UTC, datetime

import pytest
from structlog.testing import capture_logs

from engineering_memory.archive import OriginalPayload
from engineering_memory.classification import AliasProjectClassifier, ProjectRuleSet
from engineering_memory.ingestion.pipeline import IngestionPipeline
from engineering_memory.ingestion.report import RunStatus, Stage
from engineering_memory.ingestion.source import SourceConversation, SourceFormatError
from engineering_memory.ingestion.state import ImportStatus
from engineering_memory.normalization import Conversation, Message, Role, Source
from engineering_memory.sanitization.pattern_sanitizer import PatternSecretSanitizer
from tests.fakes.archive import InMemoryRawArchive
from tests.fakes.source import InMemoryConversationSource
from tests.fakes.state import InMemoryImportState
from tests.fakes.store import InMemoryMemoryStore

NOW = datetime(2026, 10, 31, tzinfo=UTC)
SECRET = "private-exception-sentinel"


def item(identity="one", text="safe text"):
    return SourceConversation(
        conversation=Conversation(
            source=Source.CHATGPT,
            source_id=identity,
            started_at=NOW,
            messages=(Message(role=Role.USER, text=text),),
        ),
        original=OriginalPayload(content=b"original bytes", media_type="text/plain"),
    )


@pytest.fixture
def parts():
    return dict(
        sanitizer=PatternSecretSanitizer(),
        classifier=AliasProjectClassifier(ProjectRuleSet()),
        archive=InMemoryRawArchive(),
        memory=InMemoryMemoryStore(),
        state=InMemoryImportState(),
        importer_version="test",
        clock=lambda: NOW,
    )


def test_recoverable_parser_failure_does_not_close_consumer(parts):
    source = InMemoryConversationSource(
        tuple(item(i) for i in ("one", "bad", "last")), unreadable=frozenset({"bad"})
    )
    result = IngestionPipeline(**parts).run(source)
    assert (result.imported, result.failed, result.status) == (2, 1, RunStatus.PARTIAL_SUCCESS)
    assert [o.source_id for o in result.outcomes] == ["one", "bad", "last"]
    assert result.outcomes[1].error == Stage.SOURCE
    assert result.outcomes[1].completed_at == NOW
    assert parts["memory"].retained == ("chatgpt:one", "chatgpt:last")


@pytest.mark.parametrize(
    ("target", "method", "stage"),
    [
        ("state", "find", Stage.STATE_READ),
        ("sanitizer", "sanitize", Stage.SANITIZE),
        ("classifier", "classify", Stage.CLASSIFY),
        ("archive", "store", Stage.ARCHIVE),
        ("memory", "retain", Stage.RETAIN),
        ("state", "record", Stage.STATE_WRITE),
    ],
)
def test_each_boundary_failure_is_safe_and_next_item_runs(
    parts, monkeypatch, target, method, stage
):
    original = getattr(parts[target], method)
    calls = 0

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError(SECRET)
        return original(*args, **kwargs)

    monkeypatch.setattr(parts[target], method, fail_once)
    with capture_logs() as logs:
        result = IngestionPipeline(**parts).run(InMemoryConversationSource((item(), item("next"))))
    assert [o.status for o in result.outcomes] == [ImportStatus.FAILED, ImportStatus.IMPORTED]
    assert result.outcomes[0].error == stage
    assert SECRET not in result.model_dump_json() + str(logs) + str(parts["state"].records)
    if stage in (Stage.STATE_READ, Stage.SANITIZE, Stage.CLASSIFY, Stage.ARCHIVE):
        assert parts["memory"].retained == ("chatgpt:next",)
    assert parts["state"].find(Source.CHATGPT, "one").status == ImportStatus.FAILED
    events = [log for log in logs if log["event"] == "ingestion.operation"]
    assert [log["status"] for log in events] == ["failed", "imported"]
    assert events[1]["project"] == "unknown"
    assert all(log["duration_ms"] >= 0 for log in events)


def test_secondary_state_record_failure_preserves_primary_failure(parts, monkeypatch):
    def fail(*args):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(parts["memory"], "retain", fail)
    monkeypatch.setattr(parts["state"], "record", fail)
    result = IngestionPipeline(**parts).run(InMemoryConversationSource((item(),)))
    assert result.outcomes[0].error == Stage.RETAIN
    assert result.outcomes[0].state_record_failed
    assert result.status == RunStatus.FAILURE


def test_order_and_no_read_ahead(parts, monkeypatch):
    calls = []
    for target, method in [
        ("state", "find"),
        ("sanitizer", "sanitize"),
        ("classifier", "classify"),
        ("archive", "store"),
        ("memory", "retain"),
        ("state", "record"),
    ]:
        original = getattr(parts[target], method)

        def traced(*args, _original=original, _method=method, **kwargs):
            calls.append(_method)
            return _original(*args, **kwargs)

        monkeypatch.setattr(parts[target], method, traced)

    class SourceReader:
        source = Source.CHATGPT

        def read(self):
            yield item()
            assert calls == ["find", "sanitize", "classify", "store", "retain", "record"]
            yield item("next")

    assert IngestionPipeline(**parts).run(SourceReader()).imported == 2


def test_terminal_source_error_keeps_progress(parts):
    class BrokenSource:
        source = Source.CHATGPT

        def read(self):
            yield item()
            raise RuntimeError(SECRET)

    result = IngestionPipeline(**parts).run(BrokenSource())
    assert result.imported == 1
    assert result.terminal_error == Stage.SOURCE
    assert result.status == RunStatus.PARTIAL_SUCCESS
    assert SECRET not in result.model_dump_json()
    assert (
        IngestionPipeline(**parts).run(InMemoryConversationSource(unreachable=True)).status
        == RunStatus.FAILURE
    )


def test_parser_without_identity_is_reported_without_fabricated_state(parts):
    class Reader:
        source = Source.CHATGPT

        def read(self):
            class Items:
                count = 0

                def __next__(self):
                    self.count += 1
                    if self.count == 1:
                        raise SourceFormatError(SECRET)
                    raise StopIteration

                def __iter__(self):
                    return self

            return Items()

    result = IngestionPipeline(**parts).run(Reader())
    assert result.failed == 1
    assert result.outcomes[0].source_id is None
    assert result.outcomes[0].document_id is None
    assert not parts["state"].records


def test_enrichment_failure_is_isolated(parts):
    parts["importer_version"] = ""
    result = IngestionPipeline(**parts).run(InMemoryConversationSource((item(), item("next"))))
    assert result.failed == 2
    assert all(o.error == Stage.ENRICH for o in result.outcomes)
    assert not parts["memory"].retained


def test_interrupt_propagates_without_leaking_exception_text(parts, monkeypatch):
    def interrupt(*args):
        raise KeyboardInterrupt(SECRET)

    monkeypatch.setattr(parts["memory"], "retain", interrupt)
    with capture_logs() as logs, pytest.raises(KeyboardInterrupt):
        IngestionPipeline(**parts).run(InMemoryConversationSource((item(),)))
    assert SECRET not in str(logs)


def test_empty_source_finishes_successfully(parts):
    result = IngestionPipeline(**parts).run(InMemoryConversationSource())
    assert result.status == RunStatus.SUCCESS
    assert not result.outcomes and not parts["state"].records


def test_classifier_only_sees_sanitized_content(parts, monkeypatch):
    original = parts["classifier"].classify
    seen = []

    def classify(conversation):
        seen.append(conversation)
        assert "hunter2" not in conversation.model_dump_json()
        return original(conversation)

    monkeypatch.setattr(parts["classifier"], "classify", classify)
    result = IngestionPipeline(**parts).run(
        InMemoryConversationSource((item(text="password=hunter2"),))
    )
    assert result.imported == 1 and len(seen) == 1


def test_logging_failure_cannot_abort_import_or_discard_report(parts, monkeypatch):
    import engineering_memory.ingestion.pipeline as module

    class BrokenLogger:
        def info(self, *args, **kwargs):
            raise OSError(SECRET)

        error = info

    monkeypatch.setattr(module, "get_logger", lambda: BrokenLogger())
    result = IngestionPipeline(**parts).run(InMemoryConversationSource((item(), item("next"))))
    assert result.imported == 2
    assert parts["memory"].retained == ("chatgpt:one", "chatgpt:next")


def test_hash_failure_is_isolated_without_inventing_failed_state(parts, monkeypatch):
    original = Conversation.content_hash

    def hash_content(conversation):
        if conversation.source_id == "one":
            raise ValueError(SECRET)
        return original(conversation)

    monkeypatch.setattr(Conversation, "content_hash", hash_content)
    result = IngestionPipeline(**parts).run(InMemoryConversationSource((item(), item("next"))))
    assert result.failed == result.imported == 1
    assert result.outcomes[0].error == Stage.HASH
    assert parts["state"].find(Source.CHATGPT, "one") is None
