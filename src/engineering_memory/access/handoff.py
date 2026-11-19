"""Build a cited Markdown handoff from one sanitized archive record."""

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from ipaddress import ip_address
from itertools import zip_longest
from typing import Literal, Protocol
from urllib.parse import quote, urlencode, urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from engineering_memory.access.deep_recall import SynthesisLimit
from engineering_memory.access.service import (
    AccessError,
    SessionHandoffRequest,
    SynthesisUnconfigured,
    _document_id,
    _safe,
    _validate,
)
from engineering_memory.archive import RawArchive
from engineering_memory.normalization import Message, ProjectTag, Role

_SECTIONS = {
    "goal": "Goal",
    "decisions": "Confirmed decisions",
    "files": "Touched files",
    "checks": "Checks",
    "questions": "Open questions",
}
_PASSAGE_LIMIT = 128
_EVIDENCE_BYTES = 24 * 1024
_BRIEF_BYTES = 8 * 1024
_PARTIAL = "\nPartial coverage: some archive evidence or brief entries were omitted.\n"
_URL = re.compile(r"(?i)(?:[a-z][a-z0-9+.-]*://|www\.|mailto:)[^\s<>()\[\]]+")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b")
_CODEX_EXIT = re.compile(
    r"\AChunk ID: [^\r\n]+\r?\nWall time: [^\r\n]+\r?\n"
    r"Process exited with code (-?\d+)(?:\r?\n|\Z)"
)
_EDIT_TOOLS = {"edit", "multiedit", "write", "notebookedit", "apply_patch"}
_SHELL_TOOLS = {"bash", "powershell", "exec_command", "shell", "shell_command", "terminal"}
_MARKUP = re.compile(r"([\\\x60*_\[\]<>#!|~&])")


class HandoffSynthesizer(Protocol):
    def synthesize_handoff(
        self, passages: dict[str, str], times: dict[str, str | None]
    ) -> object: ...


@dataclass(frozen=True)
class Evidence:
    message_index: int
    field: str
    tool_index: int | None
    role: Role
    text: str
    timestamp: str | None
    tool_name: str | None

    def link(self, document_id: str, project: str, origin: str) -> str:
        params = {
            "view": "session",
            "project": project,
            "document": document_id,
            "message": str(self.message_index),
            "field": self.field,
        }
        if self.tool_index is not None:
            params["tool"] = str(self.tool_index)
        return f"{origin}#{urlencode(params, quote_via=quote)}"


class _Entry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    section: Literal["goal", "decisions", "files", "checks", "questions"]
    status: Literal["recorded", "unknown", "conflicting"]
    text: str = Field(min_length=1, max_length=300)
    selectors: list[str] = Field(max_length=3)
    outcome: Literal["changed", "passed", "failed"] | None = None


class _Draft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    entries: list[_Entry] = Field(max_length=12)


def explorer_origin(value: str | None) -> str:
    if value is None:
        return ""
    try:
        if not re.fullmatch(r"http://(?:127(?:\.[0-9]{1,3}){3}|\[::1\]):[0-9]{1,5}/?", value):
            raise ValueError
        parsed = urlsplit(value)
        if parsed.hostname and parsed.port and ip_address(parsed.hostname).is_loopback:
            return f"http://{parsed.netloc}/"
    except ValueError:
        pass
    raise AccessError("invalid_input")


def _fields(
    messages: tuple[Message, ...], positions: range
) -> Iterator[tuple[int, Message, str, int | None, str]]:
    for index in positions:
        message = messages[index]
        if message.text:
            yield index, message, "text", None, message.text
        for tool_index, tool in enumerate(message.tool_activity):
            if tool.request:
                yield index, message, "tool_request", tool_index, tool.request
            if tool.result:
                yield index, message, "tool_result", tool_index, tool.result


def _manifest(messages: tuple[Message, ...]) -> tuple[dict[str, Evidence], bool]:
    size = len(messages)
    split = min((size + 1) // 2, 128)
    right = range(size - 1, max(size - 129, split - 1), -1)
    batches = zip_longest(_fields(messages, range(split)), _fields(messages, right))
    selected = []
    remaining = _EVIDENCE_BYTES
    partial = size > 256
    for batch in batches:
        for item in batch:
            if item is None:
                continue
            index, message, field, tool, value = item
            if not remaining or len(selected) == _PASSAGE_LIMIT:
                return _indexed(selected), True
            limit = min(1024, remaining)
            excerpt = value[:limit].encode()[:limit].decode(errors="ignore")
            partial |= excerpt != value
            if excerpt.strip():
                remaining -= len(excerpt.encode())
                timestamp = message.sent_at.isoformat() if message.sent_at is not None else None
                name = message.tool_activity[tool].name[:80] if tool is not None else None
                selected.append(
                    Evidence(index, field, tool, message.role, excerpt, timestamp, name)
                )
    return _indexed(selected), partial


def _indexed(selected: list[Evidence]) -> dict[str, Evidence]:
    ordered = sorted(
        selected,
        key=lambda item: (
            item.message_index,
            -1 if item.tool_index is None else item.tool_index,
            item.field == "tool_result",
        ),
    )
    return {str(index): item for index, item in enumerate(ordered, 1)}


def _inert(text: str) -> str:
    flattened = " ".join(text.split())
    flattened = "".join(char for char in flattened if char.isprintable())
    flattened = _URL.sub("[link omitted]", flattened)
    return _MARKUP.sub(r"\\\1", _EMAIL.sub("[address omitted]", flattened))


def _object(text: str) -> dict:
    try:
        payload = json.loads(text)
    except (ValueError, RecursionError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _call_id(payload: dict, field: str) -> str | None:
    value = payload.get("call_id", payload.get("id" if field == "tool_request" else "tool_use_id"))
    return value if isinstance(value, str) and value else None


def _result_success(payload: dict) -> bool | None:
    if payload.get("is_error") is True:
        return False
    output = payload.get("output")
    code = output.get("exit_code") if isinstance(output, dict) else payload.get("exit_code")
    if type(code) is int:
        return code == 0
    if isinstance(output, str) and (marker := _CODEX_EXIT.match(output)):
        return int(marker[1]) == 0
    return True if payload.get("is_error") is False else None


def _affirms_edit(payload: dict, path: str) -> bool:
    if _result_success(payload) is False:
        return False
    text = payload.get("output", payload.get("content"))
    if not isinstance(text, str) or not text.strip():
        return False
    first, *details = text.strip().splitlines()
    if first == "Success. Updated the following files:":
        return any(line in {f"A {path}", f"D {path}", f"M {path}"} for line in details)
    return first.removesuffix(".") in {
        f"Updated {path}",
        f"Created {path}",
        f"Wrote {path}",
        f"Deleted {path}",
        f"File created successfully at: {path}",
    } or first.startswith(
        (
            f"The file {path} has been updated.",
            f"The file {path} has been updated successfully.",
            f"The file {path} has been created successfully.",
        )
    )


def _request_subject(payload: dict, name: str) -> str | None:
    arguments = payload.get("input", payload.get("arguments"))
    if isinstance(arguments, str):
        if name == "apply_patch":
            paths = re.findall(r"(?m)^\*\*\* (?:Update|Add|Delete) File: (.+)$", arguments)
            return paths[0] if len(paths) == 1 else None
        arguments = _object(arguments)
    if not isinstance(arguments, dict):
        return None
    if name in _SHELL_TOOLS:
        command = arguments.get("command", arguments.get("cmd"))
        if isinstance(command, list) and all(isinstance(part, str) for part in command):
            command = " ".join(command)
        subject = command
    else:
        subject = arguments.get("file_path", arguments.get("notebook_path"))
    return subject if isinstance(subject, str) and subject.strip() else None


def _recorded_outcome(entry: _Entry, evidence: list[Evidence]) -> str | None:
    results = [item for item in evidence if item.field == "tool_result"]
    if len(results) != 1:
        return None
    result = results[0]
    payload = _object(result.text)
    name = (result.tool_name or "").casefold()
    expected_tools = _EDIT_TOOLS if entry.section == "files" else _SHELL_TOOLS
    if name not in expected_tools:
        return None

    call_id = _call_id(payload, result.field)
    for request in evidence:
        if request.field != "tool_request" or request.tool_name != result.tool_name:
            continue
        arguments = _object(request.text)
        paired = (
            call_id == _call_id(arguments, request.field)
            if call_id is not None
            else (request.message_index, request.tool_index)
            == (result.message_index, result.tool_index)
        )
        if not paired or request.message_index > result.message_index:
            continue
        subject = _request_subject(arguments, name)
        if subject is None:
            continue
        if entry.section == "files":
            if entry.outcome == "changed" and _affirms_edit(payload, subject):
                return f"Changed {subject}"[:300]
            return None
        success = _result_success(payload)
        if success is not None and entry.outcome == ("passed" if success else "failed"):
            verb = "succeeded" if success else "failed"
            return f"Command {verb}: {subject}"[:300]
        return None
    return None


def _rows(
    draft: object, manifest: dict[str, Evidence], document_id: str, project: str, origin: str
) -> Iterator[tuple[int, str, str]]:
    try:
        entries = _Draft.model_validate(draft).entries
        for entry in entries:
            evidence = [manifest[key] for key in dict.fromkeys(entry.selectors)]
            status = entry.status
            summary = entry.text
            if status == "recorded" and entry.section in {"checks", "files"}:
                if not any(item.tool_index is not None for item in evidence):
                    raise ValueError
                observed = _recorded_outcome(entry, evidence)
                if observed is None:
                    status = "unknown"
                    summary = "The cited tool evidence does not establish the reported outcome."
                else:
                    summary = observed
            text = _inert(summary)
            if (
                not text
                or (entry.status == "recorded" and not evidence)
                or (entry.status == "conflicting" and len(evidence) < 2)
            ):
                raise ValueError
            links = []
            for item in evidence:
                label = f"message {item.message_index}"
                if item.tool_index is not None:
                    label += f", tool {item.tool_index} {item.field.removeprefix('tool_')}"
                links.append(f"[{label}]({item.link(document_id, project, origin)})")
            suffix = " · " + ", ".join(links) if links else ""
            position = max((item.message_index for item in evidence), default=-1)
            yield position, entry.section, f"- **{status.capitalize()}** — {text}{suffix}\n"
    except (KeyError, ValidationError, ValueError):
        pass
    else:
        return
    raise AccessError("synthesis_invalid")


def _render(
    document_id: str,
    project: str,
    started_at: str,
    rows: tuple[tuple[int, str, str], ...],
    partial: bool,
) -> str:
    intro = (
        f"# Session handoff\n\nSession: {_inert(document_id)} · "
        f"Project: {_inert(project)} · Started: {started_at}\n"
    )
    fallback = "Unknown: insufficient recorded evidence.\n"
    sections: dict[str, list[str]] = {key: [] for key in _SECTIONS}
    remaining = _BRIEF_BYTES - len(
        (
            intro
            + _PARTIAL
            + "".join(f"\n## {heading}\n\n{fallback}" for heading in _SECTIONS.values())
        ).encode()
    )
    for _, section, row in sorted(rows, key=lambda item: item[0]):
        length = len(row.encode())
        if length > remaining:
            partial = True
            continue
        remaining -= length
        sections[section].append(row)
    return (
        intro
        + "".join(
            f"\n## {heading}\n\n" + ("".join(sections[key]) or fallback)
            for key, heading in _SECTIONS.items()
        )
        + (_PARTIAL if partial else "")
    )


def _read_handoff(
    archive: RawArchive,
    synthesis: HandoffSynthesizer | None,
    document_id: str,
    tag: ProjectTag,
    origin: str,
) -> dict[str, str]:
    record = archive.load(document_id)
    if (
        record.document_id != document_id
        or record.provenance.source != record.conversation.source
        or record.provenance.source_id != record.conversation.source_id
    ):
        raise AccessError("corrupt_record")
    if record.provenance.project != tag.value or tag not in record.tags:
        raise AccessError("not_found")

    manifest, partial = _manifest(record.conversation.messages)
    rows = ()
    if manifest:
        if synthesis is None:
            raise SynthesisUnconfigured
        passages = {
            key: f"[message {item.message_index}, {item.role}, {item.field}"
            + (f", tool {item.tool_index}: {item.tool_name}" if item.tool_index is not None else "")
            + f"]\n{item.text}"
            for key, item in manifest.items()
        }
        times = {key: item.timestamp for key, item in manifest.items()}
        try:
            draft = synthesis.synthesize_handoff(passages, times)
        except SynthesisLimit as error:
            raise AccessError(str(error)) from None
        rows = tuple(_rows(draft, manifest, document_id, tag.value, origin))
    return {
        "markdown": _render(
            document_id, tag.value, record.conversation.started_at.isoformat(), rows, partial
        ),
    }


def session_handoff(
    archive: RawArchive,
    synthesis: HandoffSynthesizer | None,
    *,
    document_id: str,
    project: str,
    link_origin: str | None = None,
) -> dict[str, str]:
    request = _validate(SessionHandoffRequest, {"document_id": document_id, "project": project})
    selected = _document_id(request.document_id)
    tag = _validate(ProjectTag, {"value": request.project})
    origin = explorer_origin(link_origin)
    longest_fragment = Evidence(2**53 - 1, "tool_request", 2**53 - 1, Role.TOOL, "", None, None)
    if len(longest_fragment.link(selected, tag.value, "")) > 4096:
        raise AccessError("invalid_input")
    return _safe(lambda: _read_handoff(archive, synthesis, selected, tag, origin))
