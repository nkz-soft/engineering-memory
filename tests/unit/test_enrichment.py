from datetime import UTC, datetime

from engineering_memory.normalization import Conversation, Message, ProjectTag, Role, Source
from engineering_memory.normalization.enrichment import enrich


def test_enrichment_preserves_history_and_supplies_consistent_tags():
    original_time = datetime(2020, 1, 1, tzinfo=UTC)
    now = datetime(2026, 10, 31, tzinfo=UTC)
    conversation = Conversation(
        source=Source.CHATGPT,
        source_id="one",
        title="Safe title",
        started_at=original_time,
        messages=(Message(role=Role.USER, text="sanitized text"),),
    )
    result = enrich(
        conversation,
        ProjectTag(value="unknown"),
        importer_version="0.1",
        imported_at=now,
        repository="org/repo",
        user="operator",
    )
    assert result.conversation is conversation
    assert result.document_id == "chatgpt:one"
    assert result.conversation.started_at == original_time
    assert result.provenance.model_dump() == {
        "source": Source.CHATGPT,
        "source_id": "one",
        "project": "unknown",
        "repository": "org/repo",
        "title": "Safe title",
        "imported_at": now,
        "importer_version": "0.1",
    }
    assert {str(tag) for tag in result.tags} == {
        "source:chatgpt",
        "project:unknown",
        "type:conversation",
        "user:operator",
    }
