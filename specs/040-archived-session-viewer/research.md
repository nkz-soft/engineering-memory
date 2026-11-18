# Research: Archived Session Viewer

## R1 — Existing boundary

**Decision**: Reuse POST /api/conversation and MemoryAccess.get_conversation unchanged.
**Evidence**: access/service.py returns complete normalized tool_activity with offset/next_offset. api/explorer.py authenticates and delegates under ADR-014.
**Rationale**: Evidence already crosses the correct boundary.
**Alternatives**: New endpoint/index duplicates access; original transcript reads violate sanitized-only policy.

## R2 — Source envelopes

**Decision**: Preserve occurrences and decode known envelopes only for presentation, keeping literal fields available.
**Evidence**: normalization/conversation.py defines name and optional request/result. ingestion/claude_code/parser.py records request {id,input} and result {tool_use_id,is_error,content}. ingestion/codex/parser.py records request {call_id,arguments} or {call_id,input}, result {call_id,output}. Calls and results can be separate messages, including unknown-tool orphan results.
**Rationale**: Pairing by proximity corrupts parallel evidence. Missing result on one occurrence says nothing about other occurrences.
**Alternatives**: New domain fields require canonical/ingestion changes; combined execution cards risk reordering.

## R3 — Recorded diffs

**Decision**: Conservatively recognize unified/apply_patch text and known Edit old/new values; label as recorded patch/edit evidence, not confirmed repository state. Retain raw text and fallback for unknown shapes.
**Rationale**: Archived strings suffice; live files are not historical authority.
**Alternatives**: Live git breaks provenance; a remote syntax library adds unnecessary dependency/network risk.

## R4 — Pagination and targets

**Decision**: Absolute message/local tool indexes in fragments; request offset equal to target message with page_size=50. Preserve existing quote/time checks for verified citations.
**Evidence**: explorer.js already opens citations at anchor.message_index and evidenceField resolves text/tool_request/tool_result.
**Rationale**: Offsets need not align to fixed page boundaries; no prior-page scans/count endpoint needed.
**Alternatives**: Native call IDs can be absent/nonunique. Quotes in URLs expose history. Immutable archive revisions are separate scope.

## R5 — Disclosure

**Decision**: Native details/summary controls and textContent-only rendering; preview at 20 lines/2,000 characters, complete expansion.
**Rationale**: Accessible and dependency-free within current CSP. Visual bound does not promise bounded backend I/O.
**Alternatives**: Silent truncation loses evidence; virtualization/streaming needs broader design.

## Clarification Outcome

No blocking unknowns. Issue omits Alternatives and Governance sections; record absence rather than invent policy changes. Proposed defaults are explicit in spec.md for approval.
