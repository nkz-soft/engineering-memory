"""Resolve, sanitize and approve exact revisions through the local writer."""

from datetime import UTC
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from engineering_memory.access.neighborhood import checked_record
from engineering_memory.access.neighborhood_evidence import project_of, snapshot_of
from engineering_memory.access.service import AccessError, _document_id
from engineering_memory.archive import (
    ArchiveDocumentNotFound,
    ArchiveRejected,
    ArchiveUnavailable,
    RawArchive,
)
from engineering_memory.playbooks.interface import CatalogUnavailable, PlaybookWriter
from engineering_memory.playbooks.models import (
    Draft,
    DraftInput,
    Example,
    PlaybookContent,
    PlaybookKey,
    Revision,
)
from engineering_memory.sanitization.pattern_sanitizer import PatternSecretSanitizer

_REVISION = TypeAdapter(Revision)


class PlaybookOperator:
    def __init__(self, writer: PlaybookWriter, archive: RawArchive) -> None:
        self.writer = writer
        self.archive = archive
        self.sanitizer = PatternSecretSanitizer()

    def _example(self, project: str, document_id: str) -> Example:
        try:
            record = self.archive.load(_document_id(document_id))
        except (AccessError, ArchiveDocumentNotFound, ArchiveRejected, ArchiveUnavailable):
            raise ValueError("example_unavailable") from None
        if record.document_id != document_id or project_of(record) != project:
            raise ValueError("example_unavailable")
        return Example(
            project=project,
            document_id=document_id,
            source_timestamp=record.conversation.started_at.astimezone(UTC),
            snapshot=snapshot_of(record),
        )

    def stage(self, project: str, id: str, data: object) -> Draft:
        try:
            key = PlaybookKey(project=project, id=id)
            source = DraftInput.model_validate(data)
            content = PlaybookContent(
                title=self.sanitizer.redact_text(source.title)[0],
                steps=[self.sanitizer.redact_text(step)[0] for step in source.steps],
                examples=[
                    self._example(key.project, document_id) for document_id in source.examples
                ],
            )
        except ValidationError:
            raise ValueError("invalid_input") from None
        draft = Draft(revision=uuid4().hex, content=content)
        try:
            self.writer.stage(key.project, key.id, draft)
        except CatalogUnavailable:
            raise ValueError("catalog_unavailable") from None
        return draft

    def review(self, project: str, id: str) -> Draft:
        try:
            key = PlaybookKey(project=project, id=id)
            draft = self.writer.review(key.project, key.id)
        except ValidationError:
            raise ValueError("invalid_input") from None
        except CatalogUnavailable:
            raise ValueError("catalog_unavailable") from None
        if draft is None:
            raise ValueError("draft_not_found")
        return draft

    def approve(self, project: str, id: str, revision: str) -> int:
        try:
            key = PlaybookKey(project=project, id=id)
            revision = _REVISION.validate_python(revision)
            return self.writer.approve(
                key.project, key.id, revision, lambda content: self._verify(key.project, content)
            )
        except ValidationError:
            raise ValueError("invalid_input") from None
        except CatalogUnavailable:
            raise ValueError("catalog_unavailable") from None

    def _verify(self, project: str, content: PlaybookContent) -> None:
        for example in content.examples:
            try:
                checked_record(self.archive, example.document_id, project, example.snapshot)
            except AccessError:
                raise ValueError("example_unavailable") from None
