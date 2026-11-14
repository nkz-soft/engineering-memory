"""Bounded recall against one project, with citations resolved from sanitized history."""

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from itertools import islice
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr

from engineering_memory.access.service import AccessError, _document_id, _quote_matches
from engineering_memory.archive import ArchiveDocumentNotFound, ArchiveRejected, RawArchive
from engineering_memory.memory.interface import MemoryStore
from engineering_memory.normalization import ProjectTag, Source

HIT_LIMIT = 10
RECORD_LIMIT = 6
PAGE_SIZE = 25
PAGE_LIMIT = 2
EVIDENCE_BYTES = 48 * 1024
PASSAGE_LIMIT = 300
FIELD_LIMIT = 1200
_SOURCE_IDS = "|".join(re.escape(source.value) for source in Source)
_RAW_DOCUMENT_ID = re.compile(rf"\b(?:{_SOURCE_IDS}):\S", re.IGNORECASE)
_DATE = re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b")


class SynthesisLimit(RuntimeError):
    """A synthesis budget ended the attempt before validation."""


class DeepRecallSynthesizer(Protocol):
    def synthesize(
        self, query: str, passages: dict[str, str], times: dict[str, str | None]
    ) -> object: ...


class _Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selector: Annotated[StrictStr, Field(min_length=1, max_length=8)]
    quote: Annotated[StrictStr, Field(min_length=1, max_length=512)] | None = None


class _Entry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Annotated[StrictStr, Field(min_length=1, max_length=600)]
    citations: Annotated[list[_Selection], Field(min_length=1, max_length=4)]


class _Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timeline: Annotated[list[_Entry], Field(max_length=12)]
    uncertainty: StrictBool = False


@dataclass
class _Coverage:
    searches: int = 0
    hits: int = 0
    candidates: int = 0
    archive_loads: int = 0
    pages: int = 0
    fields: int = 0
    passages: int = 0
    evidence_bytes: int = 0
    skipped: Counter = field(default_factory=Counter)
    limits: set[str] = field(default_factory=set)

    def as_dict(self):
        return {
            **vars(self),
            "skipped": dict(sorted(self.skipped.items())),
            "limits": sorted(self.limits),
        }


@dataclass(frozen=True)
class _Passage:
    document_id: str
    message_index: int
    field: str
    tool_index: int | None
    timestamp: datetime | None
    text: str

    def anchor(self, quote):
        result = {
            "document_id": self.document_id,
            "message_index": self.message_index,
            "field": self.field,
            "timestamp": self.timestamp.isoformat() if self.timestamp is not None else None,
            "quote": quote,
        }
        if self.tool_index is not None:
            result["tool_index"] = self.tool_index
        return result

    def order(self):
        return (
            self.timestamp is None,
            self.timestamp,
            self.document_id,
            self.message_index,
            self.field,
            self.tool_index if self.tool_index is not None else -1,
        )


def _queries(query):
    words = re.findall(r"[\w.-]+", query)
    variants = [query]
    if words:
        variants.extend((" ".join(words), " ".join(words[-min(6, max(1, len(words) // 2)) :])))
    return dict.fromkeys(variants)


def _candidates(memory, query, tag, coverage):
    candidates, conflicts = {}, set()
    for variant in _queries(query):
        coverage.searches += 1
        hits = memory.recall(variant, (tag,), HIT_LIMIT)
        for rank, hit in enumerate(islice(hits, HIT_LIMIT), start=1):
            coverage.hits += 1
            if rank == HIT_LIMIT:
                coverage.limits.add("hit_limit")
            provenance = hit.provenance
            if provenance.project != tag.value:
                coverage.skipped["foreign_hit"] += 1
                continue
            try:
                document_id = _document_id(f"{provenance.source.value}:{provenance.source_id}")
            except AccessError:
                coverage.skipped["invalid_identity"] += 1
                continue
            previous = candidates.get(document_id)
            if previous is not None and previous[1] != provenance:
                conflicts.add(document_id)
            if previous is None or rank < previous[0]:
                candidates[document_id] = (rank, provenance)
    for document_id in conflicts:
        del candidates[document_id]
    if conflicts:
        coverage.skipped["conflicting_provenance"] = len(conflicts)
    coverage.candidates = len(candidates)
    if len(candidates) > RECORD_LIMIT:
        coverage.limits.add("archive_limit")
    return sorted(candidates.items(), key=lambda row: (row[1][0], row[0]))[:RECORD_LIMIT]


def _fields(message):
    yield "text", None, message.text
    for index, tool in enumerate(message.tool_activity):
        yield "tool_request", index, tool.request
        yield "tool_result", index, tool.result


def _evidence(archive, candidates, tag, coverage):
    manifest = {}
    for document_id, (_, provenance) in candidates:
        coverage.archive_loads += 1
        try:
            record = archive.load(document_id)
        except ArchiveDocumentNotFound:
            coverage.skipped["archive_missing"] += 1
            continue
        except ArchiveRejected:
            coverage.skipped["archive_invalid"] += 1
            continue
        if (
            record.document_id != document_id
            or record.provenance != provenance
            or record.provenance.project != tag.value
            or tag not in record.tags
        ):
            coverage.skipped["archive_mismatch"] += 1
            continue
        messages = record.conversation.messages
        if len(messages) > PAGE_SIZE * PAGE_LIMIT:
            coverage.limits.add("page_limit")
        before = len(manifest)
        for offset in range(0, min(len(messages), PAGE_SIZE * PAGE_LIMIT), PAGE_SIZE):
            coverage.pages += 1
            for index, message in enumerate(messages[offset : offset + PAGE_SIZE], start=offset):
                for name, tool_index, text in _fields(message):
                    if coverage.fields == FIELD_LIMIT:
                        coverage.limits.add("field_limit")
                        return manifest
                    coverage.fields += 1
                    if not text:
                        continue
                    if len(manifest) == PASSAGE_LIMIT:
                        coverage.limits.add("passage_limit")
                        return manifest
                    remaining = EVIDENCE_BYTES - coverage.evidence_bytes
                    # Limit UTF-8 bytes without splitting a character.
                    excerpt = (
                        text[:remaining]
                        .encode("utf-8")[:remaining]
                        .decode("utf-8", errors="ignore")
                    )
                    if excerpt.strip():
                        manifest[str(len(manifest) + 1)] = _Passage(
                            document_id, index, name, tool_index, message.sent_at, excerpt
                        )
                        coverage.passages += 1
                        coverage.evidence_bytes += len(excerpt.encode("utf-8"))
                    if excerpt != text:
                        coverage.limits.add("evidence_limit")
                        return manifest
        if len(manifest) == before:
            coverage.skipped["archive_empty"] += 1
    return manifest


def _verify(draft, manifest):
    rows = []
    validated = _Draft.model_validate(draft)
    for entry in validated.timeline:
        text = entry.text.strip()
        if (
            not text
            or re.search(r'["“”\u2018\u2019`]|\A\s*>|\n\s*>', text)
            or re.search(r"(?<!\w)'[^'\n]+'(?!\w)|[\u00ab\u00bb]", text)
            or _RAW_DOCUMENT_ID.search(text)
            or _DATE.search(text)
        ):
            raise ValueError("invalid narrative")
        citations = []
        for selection in entry.citations:
            passage = manifest[selection.selector]
            quote = " ".join(passage.text.split())[:512].rstrip()
            if selection.quote is not None:
                normalized = " ".join(selection.quote.strip('"“”').split())
                if not _quote_matches(selection.quote, (passage.text,)):
                    raise ValueError("unsupported quote")
                quote = normalized
            citations.append((passage.order(), passage.anchor(quote)))
        citations.sort(key=lambda item: item[0])
        rows.append((citations[0][0], {"text": text, "citations": [row[1] for row in citations]}))
    return [row[1] for row in sorted(rows, key=lambda row: row[0])], validated.uncertainty


def deep_recall(
    memory: MemoryStore,
    archive: RawArchive,
    synthesis: DeepRecallSynthesizer,
    query: str,
    tag: ProjectTag,
) -> dict:
    coverage = _Coverage()
    candidates = _candidates(memory, query, tag, coverage)
    manifest = _evidence(archive, candidates, tag, coverage)
    timeline = []
    uncertainty = set(coverage.skipped) | coverage.limits
    status = "insufficient_evidence"
    if manifest:
        try:
            draft = synthesis.synthesize(
                query,
                {key: passage.text for key, passage in manifest.items()},
                {
                    key: passage.timestamp.isoformat() if passage.timestamp else None
                    for key, passage in manifest.items()
                },
            )
            timeline, uncertain = _verify(draft, manifest)
        except SynthesisLimit as error:
            status = "verification_failed"
            coverage.limits.add(str(error))
            uncertainty.add(str(error))
        except (ValueError, KeyError):
            status = "verification_failed"
            uncertainty.add("unverified_synthesis")
        else:
            if uncertain:
                uncertainty.add("synthesis_uncertain")
            if timeline:
                status = "partial" if uncertainty else "completed"
    if status == "insufficient_evidence":
        uncertainty.add("insufficient_evidence")
    return {
        "project": tag.value,
        "status": status,
        "timeline": timeline,
        "coverage": coverage.as_dict(),
        "uncertainty": sorted(uncertainty),
    }
