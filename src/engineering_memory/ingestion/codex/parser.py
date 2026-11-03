"""Bounded Codex rollout parser; errors never include source values."""

import json
from contextlib import suppress
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

_EVENTS = {
    "user_message",
    "agent_message",
    "agent_reasoning",
    "token_count",
    "task_started",
    "task_complete",
    "turn_aborted",
}

_BOOKKEEPING = {"turn_context", "compacted"}
_CONTENT_MARKERS = {"input_image": NonTextKind.IMAGE, "input_audio": NonTextKind.AUDIO}


def _string(value, *, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError
    return value


def _time(value):
    result = datetime.fromisoformat(_string(value))
    if result.tzinfo is None:
        raise ValueError
    return result


def _json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _content(content):
    if not isinstance(content, list):
        raise ValueError
    parts = []
    for block in content:
        kind = _string(block["type"])
        if kind in {"input_text", "output_text"}:
            parts.append(dict(text=_string(block["text"], empty=True)))
        elif kind in _CONTENT_MARKERS:
            parts.append(
                dict(text="", non_text_parts=(NonTextPart(kind=_CONTENT_MARKERS[kind], name=kind),))
            )
        else:
            raise ValueError
    return parts or [dict(text="")]


def _response(payload, sent_at, calls):
    kind = _string(payload["type"])
    if kind == "reasoning":
        # Encrypted/internal reasoning is outside the visible-transcript contract.
        return []
    if kind == "message":
        role = payload["role"]
        role = Role.SYSTEM if role == "developer" else Role(role)
        return [
            Message(role=role, sent_at=sent_at, **part) for part in _content(payload["content"])
        ]
    if kind in {"function_call", "custom_tool_call"}:
        call_id, name = _string(payload["call_id"]), _string(payload["name"])
        if call_id in calls:
            raise ValueError
        calls[call_id] = name
        key = "arguments" if kind == "function_call" else "input"
        value = _string(payload[key], empty=True)
        if key == "arguments":
            # Decode JSON arguments before wrapping, so nested secret scanning sees text leaves.
            # Incomplete argument JSON is preserved for failed tool calls.
            with suppress(ValueError):
                value = json.loads(value)
        tool = ToolActivity(name=name, request=_json({"call_id": call_id, key: value}))
        return [Message(role=Role.ASSISTANT, text="", sent_at=sent_at, tool_activity=(tool,))]
    if kind in {"function_call_output", "custom_tool_call_output"}:
        call_id = _string(payload["call_id"])
        output = payload["output"]
        markers = ()
        if isinstance(output, list):
            parts = _content(output)
            markers = tuple(marker for part in parts for marker in part.get("non_text_parts", ()))
            output = "\n".join(part["text"] for part in parts)
        else:
            output = _string(output, empty=True)
            with suppress(ValueError):
                output = json.loads(output)
        tool = ToolActivity(
            name=calls.get(call_id, "unknown-tool"),
            result=_json({"call_id": call_id, "output": output}),
        )
        return [
            Message(
                role=Role.TOOL,
                text="",
                sent_at=sent_at,
                tool_activity=(tool,),
                non_text_parts=markers,
            )
        ]
    raise ValueError


def parse_session(raw: bytes) -> Conversation:
    """Read a complete snapshot, rejecting partial or ambiguous histories as a unit."""
    try:
        return _parse(raw)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
        raise SourceFormatError("the Codex session could not be parsed") from None


def _parse(raw):
    metadata = None
    messages, times, calls = [], [], {}
    mirrored_dialogue = False
    response_seen = False
    for line in raw.decode("utf-8").split("\n"):
        if not line.strip():
            continue
        record = json.loads(line)
        kind = _string(record["type"])
        payload = record["payload"]
        if not isinstance(payload, dict):
            raise ValueError
        if kind == "session_meta":
            if metadata is not None:
                raise ValueError
            metadata = payload
            _string(payload["id"])
            times.append(_time(payload["timestamp"]))
            for field in ("cwd",):
                if payload.get(field) is not None:
                    _string(payload[field])
        elif kind == "event_msg":
            event = _string(payload["type"])
            if event not in _EVENTS:
                raise ValueError
            mirrored_dialogue |= event in {"user_message", "agent_message"}
        elif kind in _BOOKKEEPING:
            continue
        elif kind == "response_item":
            sent_at = _time(record["timestamp"])
            times.append(sent_at)
            normalized = _response(payload, sent_at, calls)
            response_seen |= bool(normalized)
            messages.extend(normalized)
        else:
            raise ValueError
    if metadata is None or (mirrored_dialogue and not response_seen):
        raise ValueError
    git = metadata.get("git") or {}
    if not isinstance(git, dict):
        raise ValueError
    repository = git.get("repository_url")
    if repository is not None:
        _string(repository)
    return Conversation(
        source=Source.CODEX,
        source_id=metadata["id"],
        started_at=min(times),
        last_activity_at=max(times),
        messages=tuple(messages),
        working_directory=metadata.get("cwd"),
        repository=repository,
    )
