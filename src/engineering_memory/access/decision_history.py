"""Build a transient decision history from verified, project-scoped archive evidence."""

from collections import Counter
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr

from engineering_memory.access.deep_recall import (
    SynthesisLimit,
    _anchor,
    _Coverage,
    _find_evidence,
    _Selection,
    _synthesis_inputs,
    _verified_text,
)
from engineering_memory.archive import RawArchive
from engineering_memory.memory.interface import MemoryStore
from engineering_memory.normalization import ProjectTag

Narrative = Annotated[StrictStr, Field(min_length=1, max_length=600)]
Kind = Literal["proposal", "adoption", "revision", "supersession"]


class _Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Kind
    version: Narrative
    prior_version: Narrative | None = None
    reason: Narrative | None = None
    action: _Selection
    context: list[_Selection] = Field(default_factory=list, max_length=3)
    chronology_disputed: StrictBool = False


class _Account(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: Narrative
    citations: list[_Selection] = Field(min_length=1, max_length=4)


class _Conflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: Narrative
    accounts: list[_Account] = Field(min_length=2, max_length=4)


class _Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[_Event] = Field(max_length=12)
    conflicts: list[_Conflict] = Field(default_factory=list, max_length=6)
    uncertainty: StrictBool = False


def _message_key(anchor):
    return anchor["document_id"], anchor["message_index"]


def _normalized(text):
    return " ".join(text.casefold().split())


def _cited_phrase(text, citations):
    return any(_normalized(text) in _normalized(citation["quote"]) for citation in citations)


def _event_rows(draft, manifest, uncertainty):
    rows = {}
    for entry in draft.events:
        action = _anchor(entry.action, manifest)
        context = [_anchor(selection, manifest) for selection in entry.context]
        version = _verified_text(entry.version)
        prior = _verified_text(entry.prior_version) if entry.prior_version is not None else None
        citations = [action, *context]
        if entry.kind == "supersession" and (
            prior is None
            or _normalized(prior) == _normalized(version)
            or not _cited_phrase(prior, citations)
        ):
            raise ValueError("unsupported prior decision version")
        reason = _verified_text(entry.reason) if entry.reason is not None else None
        if reason is not None and not _cited_phrase(reason, citations):
            raise ValueError("unsupported decision reason")

        timestamp = manifest[entry.action.selector].timestamp
        if entry.chronology_disputed:
            chronology = "disputed"
            uncertainty.add("disputed_time")
        elif timestamp is None or timestamp.utcoffset() is None:
            chronology = "unknown"
            uncertainty.add("unknown_time")
        else:
            chronology = "known"
        row = {
            "kind": entry.kind,
            "version": version,
            "prior_version": prior,
            "reason": reason,
            "action": action,
            "context": context,
            "occurred_at": action["timestamp"] if chronology == "known" else None,
            "chronology": chronology,
            "ordering_uncertain": False,
        }
        key = (*_message_key(action), entry.kind)
        existing = rows.setdefault(key, row)
        if any(
            existing[field] != row[field]
            for field in ("version", "prior_version", "reason", "chronology")
        ):
            raise ValueError("incompatible duplicate event")

    def instant(row):
        timestamp = row["occurred_at"]
        return datetime.fromisoformat(timestamp) if timestamp is not None else None

    times = Counter(instant(row) for row in rows.values() if row["occurred_at"] is not None)
    for row in rows.values():
        if times[instant(row)] > 1:
            row["ordering_uncertain"] = True
            uncertainty.add("tied_time")
    return sorted(
        rows.values(),
        key=lambda row: (
            row["chronology"] != "known",
            instant(row),
            *_message_key(row["action"]),
            row["kind"],
        ),
    )


def _conflict_rows(draft, manifest):
    conflicts = []
    for conflict in draft.conflicts:
        accounts = []
        texts = set()
        sources = []
        for account in conflict.accounts:
            text = _verified_text(account.text)
            citations = [_anchor(selection, manifest) for selection in account.citations]
            texts.add(" ".join(text.casefold().split()))
            sources.append(
                {
                    (
                        *_message_key(anchor),
                        anchor["field"],
                        anchor.get("tool_index"),
                        anchor["quote"],
                    )
                    for anchor in citations
                }
            )
            accounts.append({"text": text, "citations": citations})
        if len(texts) != len(accounts) or any(
            not evidence.difference(*sources[:index], *sources[index + 1 :])
            for index, evidence in enumerate(sources)
        ):
            raise ValueError("missing distinct conflict evidence")
        conflicts.append({"summary": _verified_text(conflict.summary), "accounts": accounts})
    return conflicts


def decision_history(
    memory: MemoryStore,
    archive: RawArchive,
    synthesis,
    query: str,
    tag: ProjectTag,
) -> dict:
    coverage = _Coverage()
    manifest = _find_evidence(memory, archive, query, tag, coverage)
    uncertainty = set(coverage.skipped) | coverage.limits
    status = "insufficient_evidence"
    events, conflicts = [], []
    if manifest:
        try:
            draft = _Draft.model_validate(
                synthesis.synthesize_decisions(query, *_synthesis_inputs(manifest))
            )
            chronology_uncertainty = set()
            verified_events = _event_rows(draft, manifest, chronology_uncertainty)
            verified_conflicts = _conflict_rows(draft, manifest)
        except SynthesisLimit as error:
            status = "verification_failed"
            coverage.limits.add(str(error))
            uncertainty.add(str(error))
        except (ValueError, KeyError):
            status = "verification_failed"
            uncertainty.add("unverified_synthesis")
        else:
            events, conflicts = verified_events, verified_conflicts
            uncertainty.update(chronology_uncertainty)
            if draft.uncertainty:
                uncertainty.add("synthesis_uncertain")
            if conflicts:
                uncertainty.add("unresolved_conflict")
            if events or conflicts:
                status = "partial" if uncertainty else "completed"
    if status == "insufficient_evidence":
        uncertainty.add(status)
    return {
        "project": tag.value,
        "topic": query,
        "status": status,
        "events": events,
        "conflicts": conflicts,
        "coverage": coverage.as_dict(),
        "uncertainty": sorted(uncertainty),
    }
