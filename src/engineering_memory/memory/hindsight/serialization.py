"""Versioned engine wire representation; no transport or public engine types."""

from pydantic import ValidationError

from engineering_memory.memory.interface import MemoryStoreRejected, RecallResult
from engineering_memory.normalization import EnrichedConversation, Provenance

VERSION = "engineering_memory.version"
PROVENANCE = "engineering_memory.provenance"


def item_for(enriched: EnrichedConversation) -> dict:
    conversation = enriched.conversation
    if not any(
        m.text.strip() or m.tool_activity or m.non_text_parts for m in conversation.messages
    ):
        raise MemoryStoreRejected("empty conversation")
    return {
        "content": conversation.model_dump_json(indent=2),
        "document_id": enriched.document_id,
        "timestamp": conversation.started_at.isoformat(),
        "update_mode": "replace",
        "tags": [str(tag) for tag in enriched.tags],
        "metadata": {
            VERSION: "1",
            PROVENANCE: enriched.provenance.model_dump_json(),
            "engineering_memory.started_at": conversation.started_at.isoformat(),
        },
    }


def decode_result(fact: dict, required_tags: list[str]) -> RecallResult:
    try:
        metadata = fact["metadata"]
        if metadata[VERSION] != "1":
            raise ValueError
        provenance = Provenance.model_validate_json(metadata[PROVENANCE])
        if fact["document_id"] != f"{provenance.source.value}:{provenance.source_id}":
            raise ValueError
        if required_tags and not set(required_tags) <= set(fact["tags"]):
            raise ValueError
        return RecallResult(content=fact["text"], provenance=provenance)
    except (KeyError, TypeError, ValueError, ValidationError):
        raise MemoryStoreRejected("invalid recall provenance or content") from None
