"""Versioned engine wire representation; no transport or public engine types."""

from pydantic import ValidationError

from engineering_memory.memory.interface import MemoryStoreRejected, RecallResult, ReflectionResult
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
        provenance = _decode_provenance(fact)
        if required_tags and not set(required_tags) <= set(fact["tags"]):
            raise ValueError
        return RecallResult(content=fact["text"], provenance=provenance)
    except (KeyError, TypeError, ValueError, ValidationError):
        raise MemoryStoreRejected("invalid recall provenance or content") from None


def _decode_provenance(fact: dict) -> Provenance:
    metadata = fact["metadata"]
    if metadata[VERSION] != "1":
        raise ValueError
    provenance = Provenance.model_validate_json(metadata[PROVENANCE])
    if fact["document_id"] != f"{provenance.source.value}:{provenance.source_id}":
        raise ValueError
    return provenance


def decode_reflection(result: dict, required_tags: list[str]) -> ReflectionResult:
    try:
        answer = result["text"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError
        based_on = result.get("based_on")
        memories = [] if based_on is None else based_on["memories"]
        if not isinstance(memories, list) or any(not isinstance(fact, dict) for fact in memories):
            raise ValueError
        evidence = []
        scope = set(required_tags)
        projects = {tag for tag in scope if tag.startswith("project:")}
        for fact in memories:
            tags = fact.get("tags")
            if tags is not None:
                if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                    raise ValueError
                if projects and any(
                    tag.startswith("project:") and tag not in projects for tag in tags
                ):
                    return ReflectionResult(answer=answer)
            try:
                provenance = _decode_provenance(fact)
            except (KeyError, TypeError, ValueError):
                # Derived evidence can lack a conversation identity.
                continue
            if projects and f"project:{provenance.project}" not in projects:
                return ReflectionResult(answer=answer)
            if tags is not None and scope.issubset(tags):
                evidence.append(provenance)
        return ReflectionResult(answer=answer, evidence=tuple(evidence))
    except (KeyError, TypeError, ValueError):
        raise MemoryStoreRejected("invalid reflection response") from None
