# Feature Specification: Evidence-grounded Deep Recall

**Feature Branch**: `034-deep-recall`
**Created**: 2026-11-13
**Status**: Draft
**Input**: [Issue #82](https://github.com/nkz-soft/engineering-memory/issues/82)

## User Scenarios & Testing

### User Story 1 — Reconstruct a decision across sessions (P1)

An engineer asks how a decision changed within one project. Deep Recall finds relevant imported sessions, reads their sanitized evidence, and returns a chronological answer that the engineer can verify.

**Independent test**: Import a synthetic Claude Code session proposing an approach and a synthetic Codex session reversing it. Ask the same question via the CLI and MCP. Each answer must describe both events in order and cite both documents at the supporting messages. Return the same session from several searches to confirm it consumes only one session slot.

### User Story 2 — See the limits of an answer (P2)

An engineer can distinguish bounded coverage from missing evidence and can inspect exactly what supports each claim.

**Independent test**: Run with a fixture in which a search or evidence budget stops the run before all candidates are read. The result reports which limit stopped it. With no usable evidence it reports insufficient evidence. A candidate answer with an invented quotation, or a real quotation attributed to the wrong message, is rejected.

### User Story 3 — Keep history within the selected project (P3)

An engineer explicitly chooses one classified project. Similarly named, unclassified, or incorrectly indexed sessions must not contribute evidence.

**Independent test**: Return foreign hits from a faulty retrieval adapter, including a prefix match, and an in-scope hit resolving to an archive record with inconsistent scope. Verify no archive read is attempted for known foreign hits and no mismatched record text reaches synthesis, answers, or diagnostics.

### Edge Cases

- Blank question, absent project, an unknown request field, or the reserved unclassified project is invalid.
- Duplicate candidates merge by stable document ID. Missing or inconsistent records are counted as skipped; they cannot support a claim.
- A page or candidate cut short by a cap is disclosed. Having no support in the examined history cannot establish that an event never happened.
- Malformed synthesis, unknown anchors, invented dates or quotes, and provider failure do not yield a trusted answer.

## Requirements

- **FR-001**: Provide one read-only capability on both CLI and MCP, requiring a question and exact classified project.
- **FR-002**: Run a bounded, deduplicated set of searches using that exact project. Bound candidates, archive pages, evidence size and synthesis work per request.
- **FR-003**: Check candidate provenance before archive access, and verify archive identity and exact scope before selecting any message or tool text.
- **FR-004**: Use sanitized archive pages as the evidence of record. Treat all history as data, and send only in-scope evidence to an explicitly configured synthesis backend.
- **FR-005**: Present events in evidence time order. Every returned evidence-based entry must cite a stable document ID and addressable message anchor. Verify any returned quote against its selected sanitized field.
- **FR-006**: Return structured coverage and uncertainty, including skipped evidence and explicit budget limits. Return no answer when there is no usable evidence or validation fails.
- **FR-007**: Do not write to memory, archive or import state. Do not expose originals, private exception details, or request/evidence content in diagnostics.

### Key Entities

- **Recall request**: Question plus exact project.
- **Evidence anchor**: Stable document ID, archive message position and field; timestamp and quote derive from the archive.
- **Recall result**: Status, chronological supported entries, coverage and uncertainty.

## Success Criteria

- **SC-001**: The cross-source acceptance fixture produces a chronological result with one or more resolving anchors from each source on both interfaces.
- **SC-002**: Every fabricated quote, misattributed quote and unobserved anchor in the negative contract fixtures is rejected.
- **SC-003**: Under missing evidence and each forced cap, the result records the corresponding uncertainty or coverage limit and measured work never exceeds the cap.
- **SC-004**: Scope fixtures permit zero known foreign archive lookups and zero foreign evidence bytes in synthesis input and public output.

## Assumptions

- Existing retention and access operations remain available. No new history source, bank, or persistent recall report is required.
- Evidence positions use the archive's existing ordered messages, resolved through conversation paging; no new global message ID is needed.
- A first release favors bounded coverage and visible gaps over exhaustive history. Structured coverage is descriptive, not a score for corpus completeness.
