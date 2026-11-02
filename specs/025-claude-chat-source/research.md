# Research: Claude chat source

## R1 — Export evidence and supported dialect

**Decision**: Bound initial support to the explicit fixture dialect in data-model.md.
**Evidence**: Anthropic's [export help](https://support.claude.com/en/articles/9450526-export-your-claude-data)
confirms downloadable conversation exports, but does not publish a normative field schema.
The field mapping here is an assumption to validate with synthetic fixtures and, before claiming
broad compatibility, an operator's local export. No real export was inspected in Phase 1.
**Rationale**: Avoid inventing a stable vendor contract. Reject incompatible records without
losing originals or leaking values.
**Alternatives considered**: Compliance API and live scraping are separate products/formats.

## R2 — Registration

**Decision**: Add `--source chatgpt|claude-chat` to import; default chatgpt, used for export and
archive input. Reject other enum members until separately implemented, before opening state or memory.
**Evidence**: cli/runtime.py currently directly selects ChatGPTExportSource/ChatGPTArchiveSource;
normalization/conversation.py already defines CLAUDE_CHAT and deterministic document ids.
**Rationale**: Explicit selection permits identical conversations.json filenames and no guessing.
**Alternatives considered**: Auto-detection and a second import command complicate existing behavior.

## R3 — Streaming, replay and failure isolation

**Decision**: Reuse chatgpt/records.py RecordScanner without modification; own a resumable iterator
and source-local packaging policy. Accept direct conversations.json, directory root conversations.json,
and one root conversations.json in ZIP; reject ambiguous/missing entries and do not extract ZIPs.
Replay uses archive.iter_document_ids(source=Source.CLAUDE_CHAT) and load_original, reparsing each record.
**Rationale**: Source contract requires repeatability and continued iteration after a malformed
record; a raising generator cannot satisfy it. Preserve raw JSON slices as application/json bytes.
**Alternatives considered**: Loading the entire export, duplicating scanning, or replaying normalized
snapshots would weaken streaming or original-based reconstruction guarantees.

## R4 — Existing downstream support

**Decision**: No pipeline, model, archive/state, memory or access changes.
**Evidence**: Source enum, computed document id, generic provenance/tags and archive filtering
already support claude-chat. Contract suite is tests/contracts/source.py.
**Rationale**: Prove the replaceable source boundary by exercising actual shared stages.
**Alternatives considered**: Specialized storage or source-specific memory tags contradict #26.

## R5 — Unsupported content and diagnostics

**Decision**: Normalize ordered text blocks; when structured content exists use it as authoritative,
with legacy text only as fallback, avoiding doubled text. Use explicit non-text markers for opaque
blocks/attachments; preserve full originals. Unknown sender or invalid required fields fail the
record. Diagnostics contain error categories/field locations, never input values or payload repr.
**Rationale**: Existing model carries non-text markers and cannot represent arbitrary vendor blocks.
**Alternatives considered**: Silently dropping blocks hides data loss; flattening arbitrary objects
could index secrets/metadata outside the intended text handling.
