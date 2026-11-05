"""Read-only retrieval over engine-neutral boundaries (ADR-008)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, TypeAdapter

from engineering_memory.archive import (
    ArchiveDocumentNotFound,
    ArchiveRejected,
    ArchiveUnavailable,
    RawArchive,
)
from engineering_memory.memory.interface import (
    MemoryStore,
    MemoryStoreRejected,
    MemoryStoreUnavailable,
)
from engineering_memory.memory.interface.project_models import ProjectModelKey, ProjectModelReader
from engineering_memory.normalization import AnyTag, Source
from engineering_memory.normalization.base import OpaqueIdentifier

_TAG = TypeAdapter(AnyTag)
_ID = TypeAdapter(OpaqueIdentifier)


class AccessError(RuntimeError):
    """A fixed, public error code; underlying exception details never leave the service."""


def _safe[T](action: Callable[[], T]) -> T:
    try:
        return action()
    except AccessError as error:
        code = str(error)
    except ArchiveDocumentNotFound:
        code = "not_found"
    except ArchiveRejected:
        code = "corrupt_record"
    except (ArchiveUnavailable, MemoryStoreUnavailable):
        code = "unavailable"
    except MemoryStoreRejected:
        code = "rejected"
    except Exception:
        code = "internal"
    # Outside the handler so even __context__ cannot expose boundary exceptions.
    raise AccessError(code)


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchRequest(_Request):
    query: StrictStr
    tags: list[StrictStr] = Field(default_factory=list)
    limit: Annotated[StrictInt, Field(ge=1, le=100)] = 10


class ConversationRequest(_Request):
    document_id: StrictStr
    offset: Annotated[StrictInt, Field(ge=0)] = 0
    page_size: Annotated[StrictInt, Field(ge=1, le=100)] = 50


class ProjectModelRequest(_Request):
    project: StrictStr
    kind: StrictStr


def _validate(model, values):
    try:
        return model.model_validate(values)
    except Exception:
        pass
    raise AccessError("invalid_input")


def _tags(values):
    try:
        return tuple(
            _TAG.validate_python(
                dict(zip(("namespace", "value"), value.split(":", 1), strict=True))
            )
            for value in values
        )
    except Exception:
        pass
    raise AccessError("invalid_input")


def _document_id(value):
    try:
        source, native = value.split(":", 1)
        Source(source)
        _ID.validate_python(native)
        if any(part in native for part in ("/", "\\", "..")):
            raise ValueError
        return value
    except Exception:
        pass
    raise AccessError("invalid_input")


def _message_texts(message):
    yield " ".join(message.text.split())
    for activity in message.tool_activity:
        for text in (activity.request, activity.result):
            if text is not None:
                yield " ".join(text.split())


def _verify_evidence_quotes(content, source_texts):
    lines = content.splitlines()
    quotes = []
    for index, line in enumerate(lines):
        if (
            line.lstrip().startswith(">")
            and not line.lstrip().startswith("> ")
            and line.strip() != ">"
        ):
            raise AccessError("corrupt_record")
        if line.lstrip().startswith("> "):
            if (
                index + 1 < len(lines)
                and lines[index + 1].strip()
                and not lines[index + 1].lstrip().startswith(">")
            ):
                raise AccessError("corrupt_record")
            quotes.append(line.lstrip()[2:].strip())
    if not quotes or len(quotes) > 128:
        raise AccessError("corrupt_record")
    for quote in quotes:
        normalized = " ".join(quote.strip('"“”').split())
        if not normalized or not any(normalized in source for source in source_texts):
            raise AccessError("corrupt_record")


class MemoryAccess:
    """No concrete adapters, provisioning, importer or write calls belong here."""

    def __init__(
        self, memory: MemoryStore, archive: RawArchive, *, models: ProjectModelReader | None = None
    ):
        self.memory = memory
        self.archive = archive
        self.models = models

    def get_project_model(self, **arguments) -> dict:
        request = _validate(ProjectModelRequest, arguments)
        key = _validate(ProjectModelKey, request.model_dump())

        def read():
            if self.models is None:
                raise AccessError("unavailable")
            result = self.models.get_project_model(key)
            if result.key != key:
                raise AccessError("corrupt_record")
            response = {**key.model_dump(mode="json"), "status": result.status}
            if result.status != "ready":
                if result.last_refresh_failed_at is not None:
                    response["last_refresh_failed_at"] = result.model_dump(mode="json")[
                        "last_refresh_failed_at"
                    ]
                return response
            snapshot = result.snapshot
            if not snapshot.supports:
                raise AccessError("corrupt_record")
            supports, source_texts, messages = [], [], {}
            for support in snapshot.supports:
                document_id = _document_id(support.document_id)
                archived = self.archive.load(document_id)
                if (
                    archived.document_id != document_id
                    or archived.provenance != support.provenance
                    or archived.provenance.project != key.project
                    or f"project:{key.project}" not in {str(tag) for tag in archived.tags}
                ):
                    raise AccessError("corrupt_record")
                messages[document_id] = archived.conversation.messages
                for message in archived.conversation.messages:
                    source_texts.extend(_message_texts(message))
                supports.append(
                    {
                        "document_id": document_id,
                        "provenance": archived.provenance.model_dump(mode="json"),
                        "started_at": archived.conversation.model_dump(mode="json")["started_at"],
                    }
                )
            content = snapshot.content
            if snapshot.evidence_selectors:
                if len(snapshot.evidence_selectors) > 128 or any(
                    line.lstrip().startswith(">") for line in content.splitlines()
                ):
                    raise AccessError("corrupt_record")
                quotes = []
                for selector in snapshot.evidence_selectors:
                    selected = messages.get(selector.document_id, ())
                    if selector.message_index >= len(selected):
                        raise AccessError("corrupt_record")
                    excerpt = " ".join(selected[selector.message_index].text.split())
                    if not excerpt:
                        raise AccessError("corrupt_record")
                    quotes.append(f"> {excerpt}")
                content = "\n\n".join([content, *dict.fromkeys(quotes)])
            _verify_evidence_quotes(content, source_texts)
            response.update(
                snapshot.model_dump(mode="json", exclude={"supports", "evidence_selectors"})
            )
            response["content"] = content
            response["supports"] = supports
            return response

        return _safe(read)

    def search_memory(self, **arguments) -> dict:
        request = _validate(SearchRequest, arguments)
        if not request.query.strip():
            raise AccessError("invalid_input")
        tags = _tags(request.tags)

        def read():
            results = []
            for match in self.memory.recall(request.query, tags, request.limit):
                document_id = f"{match.provenance.source.value}:{match.provenance.source_id}"
                archived = self.archive.load(document_id)
                if archived.document_id != document_id:
                    raise AccessError("corrupt_record")
                results.append(
                    {
                        "content": match.content,
                        "document_id": document_id,
                        "provenance": match.provenance.model_dump(mode="json"),
                        "started_at": archived.conversation.model_dump(mode="json")["started_at"],
                        "score": match.score,
                    }
                )
            return {"results": results}

        return _safe(read)

    def get_conversation(self, **arguments) -> dict:
        request = _validate(ConversationRequest, arguments)
        document_id = _document_id(request.document_id)

        def read():
            archived = self.archive.load(document_id)
            if archived.document_id != document_id:
                raise AccessError("corrupt_record")
            conversation = archived.conversation
            end = request.offset + request.page_size
            return {
                "document_id": document_id,
                "provenance": archived.provenance.model_dump(mode="json"),
                "started_at": conversation.model_dump(mode="json")["started_at"],
                "messages": [
                    m.model_dump(mode="json") for m in conversation.messages[request.offset : end]
                ],
                "offset": request.offset,
                "next_offset": end if end < len(conversation.messages) else None,
            }

        return _safe(read)
