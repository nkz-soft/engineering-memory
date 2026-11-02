"""Bounded JSONL snapshot dialect; diagnostics never expose a record's values."""

import json
from datetime import datetime

from engineering_memory.ingestion.source import SourceFormatError
from engineering_memory.normalization import (
    Conversation,
    Message,
    NonTextKind,
    NonTextPart,
    Role,
    Source,
    ToolActivity,
)

_OPERATIONAL = {"progress", "summary", "file-history-snapshot", "queue-operation", "system"}


def _string(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError
    return value


def _json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _marker(name):
    return NonTextPart(kind=NonTextKind.OTHER, name=name)


def _result_content(value):
    if isinstance(value, str):
        return value, ()
    if not isinstance(value, list):
        raise ValueError
    parts, markers = [], []
    for block in value:
        if not isinstance(block, dict):
            raise ValueError
        kind = _string(block.get("type"))
        if kind == "text":
            if not isinstance(block.get("text"), str):
                raise ValueError
            parts.append(block["text"])
        else:
            markers.append(_marker(kind))
    return "\n".join(parts), tuple(markers)


def _messages(record, calls, sent_at):
    role = Role(record["type"])
    content = record["message"]["content"]
    if isinstance(content, str):
        return [Message(role=role, text=content, sent_at=sent_at)]
    if not isinstance(content, list):
        raise ValueError
    messages = []
    for block in content:
        if not isinstance(block, dict):
            raise ValueError
        kind = _string(block.get("type"))
        fields = dict(role=role, text="", sent_at=sent_at)
        if kind == "text":
            if not isinstance(block.get("text"), str):
                raise ValueError
            fields["text"] = block["text"]
        elif kind == "tool_use":
            call_id, name = _string(block.get("id")), _string(block.get("name"))
            if call_id in calls or not isinstance(block.get("input"), dict):
                raise ValueError
            calls[call_id] = name
            fields["tool_activity"] = (
                ToolActivity(name=name, request=_json({"id": call_id, "input": block["input"]})),
            )
        elif kind == "tool_result":
            call_id = _string(block.get("tool_use_id"))
            error = block.get("is_error", False)
            if not isinstance(error, bool):
                raise ValueError
            text, markers = _result_content(block.get("content", ""))
            fields.update(
                role=Role.TOOL,
                non_text_parts=markers,
                tool_activity=(
                    ToolActivity(
                        name=calls.get(call_id, "unknown-tool"),
                        result=_json({"tool_use_id": call_id, "is_error": error, "content": text}),
                    ),
                ),
            )
        else:
            fields["non_text_parts"] = (_marker(kind),)
        messages.append(Message(**fields))
    return messages or [Message(role=role, text="", sent_at=sent_at)]


def parse_session(raw: bytes) -> Conversation | None:
    """Normalize one entire snapshot, or fail it as a unit (never a partial chain)."""
    try:
        return _parse(raw)
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError):
        raise SourceFormatError("the Claude Code session could not be parsed") from None


def _parse(raw):
    messages, times, seen, calls = [], [], set(), {}
    session_id = repository = cwd = None
    # JSONL records end at LF; Unicode paragraph separators are valid JSON string content.
    for line in raw.decode("utf-8").split("\n"):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError
        kind = _string(record.get("type"))
        if kind in _OPERATIONAL:
            continue
        if record.get("isSidechain") is True:
            messages.append(
                Message(role=Role.SYSTEM, text="", non_text_parts=(_marker("sidechain"),))
            )
            continue
        if kind not in {"user", "assistant"}:
            messages.append(Message(role=Role.SYSTEM, text="", non_text_parts=(_marker(kind),)))
            continue
        native = _string(record.get("sessionId"))
        if session_id is not None and native != session_id:
            raise ValueError
        session_id = native
        uuid = _string(record.get("uuid"))
        if uuid in seen:
            raise ValueError
        seen.add(uuid)
        sent_at = datetime.fromisoformat(_string(record.get("timestamp")))
        if sent_at.tzinfo is None:
            raise ValueError
        times.append(sent_at)
        for key in ("repository", "cwd"):
            value = record.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError
        repository = repository or (record.get("repository") or "").strip() or None
        cwd = cwd or (record.get("cwd") or "").strip() or None
        messages.extend(_messages(record, calls, sent_at))
    if session_id is None:
        return None
    return Conversation(
        source=Source.CLAUDE_CODE,
        source_id=session_id,
        started_at=min(times),
        last_activity_at=max(times),
        messages=tuple(messages),
        repository=repository,
        working_directory=cwd,
    )
