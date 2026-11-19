"""Build a cited Markdown handoff from one sanitized archive record."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from ipaddress import ip_address
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

    @property
    def outcome(self) -> bool:
        return self.field == "tool_result" or (self.field == "text" and self.role == Role.TOOL)

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


def _fields(message: Message) -> Iterator[tuple[str, int | None, str | None]]:
    yield "text", None, message.text
    for index, tool in enumerate(message.tool_activity):
        yield "tool_request", index, tool.request
        yield "tool_result", index, tool.result


def _positions(size: int) -> Iterator[int]:
    if size <= 256:
        yield from range(size)
        return
    for index in range(128):
        yield index
        yield size - index - 1


def _manifest(messages: tuple[Message, ...]) -> tuple[dict[str, Evidence], bool]:
    selected = []
    remaining = _EVIDENCE_BYTES
    partial = len(messages) > 256
    for index in _positions(len(messages)):
        message = messages[index]
        timestamp = message.sent_at.isoformat() if message.sent_at is not None else None
        for field, tool, value in _fields(message):
            if not value:
                continue
            if not remaining or len(selected) == _PASSAGE_LIMIT:
                return _indexed(selected), True
            limit = min(1024, remaining)
            excerpt = value[:limit].encode()[:limit].decode(errors="ignore")
            partial |= excerpt != value
            if excerpt.strip():
                remaining -= len(excerpt.encode())
                selected.append(Evidence(index, field, tool, message.role, excerpt, timestamp))
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
    return _MARKUP.sub(r"\\\1", _URL.sub("[link omitted]", flattened))


def _rows(
    draft: object, manifest: dict[str, Evidence], document_id: str, project: str, origin: str
):
    try:
        entries = _Draft.model_validate(draft).entries
        for entry in entries:
            evidence = [manifest[key] for key in dict.fromkeys(entry.selectors)]
            text = _inert(entry.text)
            if (
                not text
                or (entry.status == "recorded" and not evidence)
                or (entry.status == "conflicting" and len(evidence) < 2)
                or (
                    entry.status == "recorded"
                    and entry.section in {"checks", "files"}
                    and not any(item.outcome for item in evidence)
                )
            ):
                raise ValueError
            links = []
            for item in evidence:
                label = f"message {item.message_index}"
                if item.tool_index is not None:
                    label += f", tool {item.tool_index} {item.field.removeprefix('tool_')}"
                links.append(f"[{label}]({item.link(document_id, project, origin)})")
            suffix = " · " + ", ".join(links) if links else ""
            yield entry.section, f"- **{entry.status.capitalize()}** — {text}{suffix}\n"
    except (KeyError, ValidationError, ValueError):
        pass
    else:
        return
    raise AccessError("synthesis_invalid")


def _render(document_id: str, project: str, started_at: str, rows, partial: bool) -> str:
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
    for section, row in rows:
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
            + (f", tool {item.tool_index}" if item.tool_index is not None else "")
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
    return _safe(lambda: _read_handoff(archive, synthesis, selected, tag, origin))
