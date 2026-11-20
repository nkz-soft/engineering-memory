"""Read a derived neighborhood and verify its evidence against the normalized archive."""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import TYPE_CHECKING, Annotated, Literal, Protocol

from pydantic import AfterValidator, Field, StrictStr, model_validator

from engineering_memory.access.service import (
    AccessError,
    ConversationRequest,
    _document_id,
    _Request,
)
from engineering_memory.archive import (
    ArchiveDocumentNotFound,
    ArchiveRejected,
    ArchiveUnavailable,
    RawArchive,
)
from engineering_memory.normalization.base import Slug

if TYPE_CHECKING:
    from engineering_memory.access.neighborhood_evidence import EvidenceEdge, Node
    from engineering_memory.normalization import EnrichedConversation


EDGE_EXCERPT_CHARS = 2_000


class NeighborhoodUnavailable(RuntimeError):
    """The projection cannot be read or rebuilt."""


class NeighborhoodReader(Protocol):
    def neighborhood(self, project: str, root: Node) -> dict: ...

    def evidence(self, project: str, handle: str) -> EvidenceEdge | None: ...


def _classified(project: str) -> str:
    if project in {"unknown", "unclassified"}:
        raise ValueError("a classified project is required")
    return project


Project = Annotated[Slug, Field(max_length=200, strict=True), AfterValidator(_classified)]
Snapshot = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
Handle = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{32}$")]


class SessionRoot(_Request):
    kind: Literal["session"]
    identity: Annotated[StrictStr, Field(min_length=1, max_length=1024)]

    @model_validator(mode="after")
    def check_identity(self):
        try:
            _document_id(self.identity)
        except AccessError:
            raise ValueError("invalid session identity") from None
        return self


class FileRoot(_Request):
    kind: Literal["file"]
    identity: Annotated[StrictStr, Field(min_length=1, max_length=1024)]
    repository: Annotated[StrictStr, Field(min_length=1, max_length=1024)]

    @model_validator(mode="after")
    def check_scope(self):
        from engineering_memory.access.neighborhood_evidence import normalize_file_path

        if normalize_file_path(self.identity) is None:
            raise ValueError("invalid repository-relative path")
        if self.repository.strip() != self.repository or not self.repository.isprintable():
            raise ValueError("invalid repository scope")
        return self


class NeighborhoodRequest(_Request):
    project: Project
    root: Annotated[SessionRoot | FileRoot, Field(discriminator="kind")]


class NeighborhoodEvidenceRequest(_Request):
    project: Project
    handle: Handle


class GuardedConversationRequest(ConversationRequest):
    project: Project | None = None
    snapshot: Snapshot | None = None

    @model_validator(mode="after")
    def check_guard(self):
        fields = self.model_fields_set
        if ("project" in fields or "snapshot" in fields) and (
            self.project is None or self.snapshot is None
        ):
            raise ValueError("a complete archive snapshot guard is required")
        return self


def graph(reader: NeighborhoodReader | None, request: NeighborhoodRequest) -> dict:
    from engineering_memory.access.neighborhood_evidence import Node, normalize_file_path

    root = request.root
    if isinstance(root, FileRoot):
        identity = normalize_file_path(root.identity)
        if identity is None:
            raise AccessError("invalid_input")
        node = Node("file", identity, identity, root.repository)
    else:
        node = Node("session", root.identity, root.identity)
    if reader is None:
        return {"root": asdict(node), "status": "unindexed", "edges": [], "truncated": False}
    try:
        return {"root": asdict(node), **reader.neighborhood(request.project, node)}
    except NeighborhoodUnavailable:
        raise AccessError("unavailable") from None


def checked_record(
    archive: RawArchive, document_id: str, project: str, snapshot: str
) -> EnrichedConversation:
    from engineering_memory.access.neighborhood_evidence import project_of, snapshot_of

    try:
        item = archive.load(document_id)
    except (ArchiveDocumentNotFound, ArchiveRejected, ArchiveUnavailable):
        raise AccessError("not_found") from None
    if (
        item.document_id != document_id
        or project_of(item) != project
        or snapshot_of(item) != snapshot
    ):
        raise AccessError("not_found")
    return item


def _field_text(item: EnrichedConversation, edge: EvidenceEdge) -> str:
    messages = item.conversation.messages
    if not 0 <= edge.message < len(messages):
        raise AccessError("not_found")
    message = messages[edge.message]
    if edge.field == "text" and edge.tool is None:
        return message.text
    if edge.tool is None or not 0 <= edge.tool < len(message.tool_activity):
        raise AccessError("not_found")
    activity = message.tool_activity[edge.tool]
    fields = {"tool_request": activity.request, "tool_result": activity.result}
    text = fields.get(edge.field)
    if text is None:
        raise AccessError("not_found")
    return text


def _excerpt(text: str, edge: EvidenceEdge) -> str:
    if len(text) <= EDGE_EXCERPT_CHARS:
        return text
    identity = edge.target.identity
    position = text.find(identity)
    if position < 0 and edge.relation == "pr_reference":
        match = re.search(re.escape(identity), text, re.IGNORECASE)
        position = match.start() if match else -1
    if position < 0 and edge.relation == "file_edit":
        for separator in ("\\", "\\\\"):
            position = text.find(identity.replace("/", separator))
            if position >= 0:
                break
        if position < 0:
            position = text.find(identity.rsplit("/", 1)[-1])
    width = EDGE_EXCERPT_CHARS - 2
    start = min(max(0, position - width // 4), len(text) - width)
    end = start + width
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def read_evidence(
    reader: NeighborhoodReader | None, archive: RawArchive, request: NeighborhoodEvidenceRequest
) -> dict:
    try:
        edge = reader.evidence(request.project, request.handle) if reader is not None else None
    except NeighborhoodUnavailable:
        raise AccessError("unavailable") from None
    if edge is None or edge.project != request.project:
        raise AccessError("not_found")
    document_id = _document_id(edge.document_id)
    item = checked_record(archive, document_id, request.project, edge.snapshot)
    return {
        "relation": edge.relation,
        "text": _excerpt(_field_text(item, edge), edge),
        "selector": {
            "document_id": document_id,
            "message": edge.message,
            "tool": edge.tool,
            "field": edge.field,
            "snapshot": edge.snapshot,
        },
    }
