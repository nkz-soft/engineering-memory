"""Issue #13 acceptance: re-ingest originals after deleting the export."""

import re
from datetime import UTC, datetime

from engineering_memory.archive import OriginalPayload
from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.classification import AliasProjectClassifier, ProjectRule, ProjectRuleSet
from engineering_memory.ingestion.chatgpt import ChatGPTExportSource
from engineering_memory.ingestion.chatgpt.archive_source import ChatGPTArchiveSource as replay
from engineering_memory.normalization import ProjectTag
from engineering_memory.sanitization import PatternSecretSanitizer, RedactionCategory
from engineering_memory.sanitization.patterns import PATTERNS, Pattern
from tests.contracts import conversations
from tests.fakes.state import InMemoryImportState
from tests.fakes.store import InMemoryMemoryStore
from tests.integration.pipeline import Pipeline
from tests.synthetic import chatgpt_export as synth

NOW = datetime(2026, 10, 26, tzinfo=UTC)


def classifier(project="engineering-memory"):
    return AliasProjectClassifier(
        ProjectRuleSet(rules=(ProjectRule(project=project, aliases=("Wolverine",)),))
    )


def test_full_ingestion_replays_from_archive_alone_under_current_rules(tmp_path):
    export = tmp_path / "conversations.json"
    items = [
        conversations.conversation("one", text="Wolverine: newly-private-marker; password=hunter2"),
        conversations.conversation("two", text="Wolverine uses durable workflow state."),
    ]
    export.write_text(
        "[" + ",".join(synth.serialize(synth.from_conversation(c)) for c in items) + "]"
    )
    archive = LocalRawArchive(tmp_path / "archive")
    first_memory = InMemoryMemoryStore()
    first = Pipeline(
        ChatGPTExportSource(export),
        PatternSecretSanitizer(),
        classifier(),
        archive,
        first_memory,
        InMemoryImportState(),
    ).run(now=NOW)
    assert first.imported == ["one", "two"]
    assert not first.failed
    assert first_memory.recall("newly-private-marker")
    assert not first_memory.recall("hunter2")
    originals = {c.document_id: archive.load_original(c.document_id) for c in items}
    export.unlink()
    assert not export.exists()
    reopened = LocalRawArchive(tmp_path / "archive")
    current_sanitizer = PatternSecretSanitizer(
        patterns=(
            *PATTERNS,
            Pattern(
                category=RedactionCategory.PASSWORD, expression=re.compile("newly-private-marker")
            ),
        )
    )
    memory = InMemoryMemoryStore()
    second = Pipeline(
        replay(reopened),
        current_sanitizer,
        classifier("reclassified"),
        reopened,
        memory,
        InMemoryImportState(),
    ).run(now=NOW)
    assert set(second.imported) == {"one", "two"}
    assert not second.failed and not second.skipped
    assert set(memory.retained) == {"chatgpt:one", "chatgpt:two"}
    assert len(memory.recall("Wolverine", tags=(ProjectTag(value="reclassified"),))) == 2
    assert not memory.recall("newly-private-marker") and not memory.recall("hunter2")
    assert memory.recall("durable workflow state")
    for item in items:
        assert reopened.load_original(item.document_id) == originals[item.document_id]
        assert reopened.load(item.document_id).conversation.started_at == item.started_at


def test_one_malformed_original_does_not_abort_full_replay(tmp_path):
    archive = LocalRawArchive(tmp_path)
    archive.store(
        conversations.enrich(conversations.conversation("bad")),
        OriginalPayload(content=b"{broken", media_type="application/json"),
    )
    good = conversations.conversation("good")
    archive.store(
        conversations.enrich(good),
        OriginalPayload(
            content=synth.serialize(synth.from_conversation(good)).encode(),
            media_type="application/json",
        ),
    )
    result = Pipeline(
        replay(archive),
        PatternSecretSanitizer(),
        classifier(),
        archive,
        InMemoryMemoryStore(),
        InMemoryImportState(),
    ).run(now=NOW)
    assert result.imported == ["good"]
    assert len(result.failed) == 1
    assert result.failed[0].source_id == "chatgpt:bad"
