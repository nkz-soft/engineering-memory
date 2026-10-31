"""Pure enrichment after sanitization and project classification."""

from datetime import datetime

from engineering_memory.normalization import (
    Conversation,
    ConversationType,
    EnrichedConversation,
    ProjectTag,
    Provenance,
    SourceTag,
    TypeTag,
    UserTag,
)
from engineering_memory.normalization.tags import AnyTag


def enrich(
    conversation: Conversation,
    project: ProjectTag,
    *,
    importer_version: str,
    imported_at: datetime,
    repository: str | None = None,
    user: str | None = None,
) -> EnrichedConversation:
    """Attach provenance without replacing original identity or conversation time."""
    tags: tuple[AnyTag, ...] = (
        SourceTag(value=conversation.source),
        project,
        TypeTag(value=ConversationType.CONVERSATION),
    )
    if user is not None:
        tags += (UserTag(value=user),)
    return EnrichedConversation(
        conversation=conversation,
        provenance=Provenance(
            source=conversation.source,
            source_id=conversation.source_id,
            project=project.value,
            repository=repository,
            title=conversation.title,
            imported_at=imported_at,
            importer_version=importer_version,
        ),
        tags=tags,
    )
