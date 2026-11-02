"""The bounded Claude export dialect of feature 025; never guess identity or time."""

from datetime import UTC, datetime

from pydantic import TypeAdapter, ValidationError

from engineering_memory.ingestion.source import SourceFormatError
from engineering_memory.normalization import (
    Conversation,
    Message,
    NonTextKind,
    NonTextPart,
    Role,
    Source,
)
from engineering_memory.normalization.base import OpaqueIdentifier

_ID = TypeAdapter(OpaqueIdentifier)


def _subject(value):
    try:
        return _ID.validate_python(value.get("uuid")) if isinstance(value, dict) else None
    except ValidationError:
        return None


def _object(value):
    if not isinstance(value, dict):
        raise ValueError("expected object")
    return value


def _array(value):
    if not isinstance(value, list):
        raise ValueError("expected array")
    return value


def _time(value, *, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("expected timestamp")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires offset")
    return parsed.astimezone(UTC)


def _message(value):
    value = _object(value)
    role = {"human": Role.USER, "assistant": Role.ASSISTANT}[value["sender"]]
    markers = []
    if "content" in value:
        texts = []
        for block in _array(value["content"]):
            block = _object(block)
            kind = block["type"]
            if not isinstance(kind, str):
                raise ValueError("block type must be text")
            if kind == "text":
                if not isinstance(block["text"], str):
                    raise ValueError("text block requires text")
                texts.append(block["text"])
            else:
                markers.append(
                    NonTextPart(kind=NonTextKind.IMAGE if kind == "image" else NonTextKind.OTHER)
                )
        text = "\n".join(texts)
    else:
        text = value["text"]
    for field in ("attachments", "files"):
        for attachment in _array(value.get(field, [])):
            attachment = _object(attachment)
            markers.append(NonTextPart(kind=NonTextKind.FILE, name=attachment.get("file_name")))
    return Message(
        role=role,
        text=text,
        sent_at=_time(value.get("created_at"), optional=True),
        non_text_parts=tuple(markers),
    )


def parse_record(value):
    """Normalize one record; boundary errors never render refused payloads."""
    try:
        value = _object(value)
        return Conversation(
            source=Source.CLAUDE_CHAT,
            source_id=value["uuid"],
            title=value.get("name"),
            started_at=_time(value["created_at"]),
            last_activity_at=_time(value.get("updated_at"), optional=True),
            messages=tuple(_message(m) for m in _array(value["chat_messages"])),
        )
    except (ValueError, TypeError, KeyError, ValidationError, RecursionError, OverflowError):
        # Do not chain an exception containing Pydantic input or arbitrary field values.
        raise SourceFormatError(
            "the Claude conversation does not fit the supported dialect", subject=_subject(value)
        ) from None
