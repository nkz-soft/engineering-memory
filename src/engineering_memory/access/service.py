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


class MemoryAccess:
    """No concrete adapters, provisioning, importer or write calls belong here."""

    def __init__(self, memory: MemoryStore, archive: RawArchive):
        self.memory = memory
        self.archive = archive

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
