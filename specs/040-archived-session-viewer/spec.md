# Feature Specification: Archived Session Viewer

**Feature Branch**: `040-archived-session-viewer`
**Created**: 2026-11-18
**Status**: Draft — awaiting human approval
**Input**: Issue #86: ordered archived Claude Code/Codex dialogue with commands, results, available textual diffs, collapsed output and exact evidence links.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inspect the investigation (Priority: P1)

An operator follows command → error → investigation → solution without paging through raw structured responses.

**Why this priority**: Tool evidence explains the conclusion.
**Independent Test**: Open synthetic sessions from both sources with dialogue, interleaved calls/results and patches.

**Acceptance Scenarios**:

1. **Given** either source, **When** opened, **Then** every message/tool occurrence appears in normalized archive order with role, available original time, name, request and result.
2. **Given** recorded textual patches or before/after edits, **When** inspected, **Then** their text is readable without consulting current files.
3. **Given** absent, empty, orphan or error results, **When** inspected, **Then** those states remain distinct and no result or success is invented.

### User Story 2 - Open exact evidence (Priority: P1)

An operator follows citations or saved links to a message or tool field beyond the first page.

**Why this priority**: Evidence must remain findable in long sessions.
**Independent Test**: Open targets at indexes 0, 49, 50 and 100 in a session exceeding 100 messages.

**Acceptance Scenarios**:

1. **Given** a valid message/tool target, **When** followed, **Then** its containing page loads and the target expands, highlights and receives focus.
2. **Given** a verified citation, **When** followed, **Then** the original timestamp and quoted-field checks still apply.
3. **Given** an invalid, missing or stale citation target, **When** followed, **Then** a visible unavailable state replaces old evidence without selecting another message.
4. **Given** a copied link, **When** reopened after refresh, **Then** authentication is required before evidence appears and the exact current-snapshot position resolves.

### User Story 3 - Scan long output safely (Priority: P2)

An operator expands only the evidence needed.

**Why this priority**: Large logs must not obscure adjacent dialogue.
**Independent Test**: Expand/collapse synthetic 10,000-line output by keyboard and follow a link into it.

**Acceptance Scenarios**:

1. **Given** long output, **When** initially shown, **Then** a bounded preview and accessible expansion control appear; expansion reveals all archived text.
2. **Given** commands, HTML, URLs or file references, **When** opened or expanded, **Then** they remain inert and cause no execution, external requests or referenced-file reads.

### Edge Cases

- Missing timestamps, empty prose, tool-only messages and non-text markers remain visible.
- Parallel calls/results split across pages retain positions and native identifiers; never pair by proximity.
- Unknown tools, malformed envelopes and unrecognized patches fall back to literal text.
- A request-only occurrence means no result on that occurrence, not proof the call never completed elsewhere.
- Lock/navigation cancels pending reads and prevents stale content restoring the prior view.
- Re-import may change positional selectors: plain links address the current snapshot; verified citations fail closed on changed evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Display sanitized archived dialogue/tool occurrences in recorded order with available provenance, roles and original timestamps.
- **FR-002**: Show requests, results, identifiers and recorded errors; distinguish absent from empty results without inferring execution status.
- **FR-003**: Show available textual patches and before/after edit evidence readably, preserve exact original text and literal fallback; never reconstruct from live files.
- **FR-004**: Collapse long fields using bounded previews and accessible full expansion; targeting a field expands it.
- **FR-005**: Support copyable message/tool links and existing verified citations across pagination, refresh and unlock with exact-target focus and unavailable states.
- **FR-006**: Preserve project validation, citation verification and authenticated local-only sanitized access.
- **FR-007**: Keep content inert: no commands, referenced-file reads, memory writes or source-service calls.
- **FR-008**: Preserve existing prose, search, Deep Recall and decision-history navigation.

### Key Entities

- **Archived session**: Existing document identity/provenance and ordered messages.
- **Message**: Absolute position, role, original time, text, tool occurrences and non-text markers.
- **Tool occurrence**: Message-local position, name and optional request/result; not a synthesized combined execution.
- **Viewer target**: Document/project/message position and optional tool field; verified citations additionally contain quote/time evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both synthetic sources display every archived message/tool occurrence once in order, including patches and missing/error cases.
- **SC-002**: Message/tool targets at 0, 49, 50 and 100 resolve exactly after opening/reloading; invalid targets visibly fail.
- **SC-003**: A 10,000-line output starts collapsed, expands completely and opens directly at a cited field without manual paging.
- **SC-004**: Adversarial text causes zero command executions, external requests or referenced-file reads; existing access/security checks remain effective.

## Assumptions

- Extend #84's explorer under ADR-014; #85 is already in the base. No new platform/service.
- Available means present in sanitized normalized archives: no originals, backfill, parser/schema migration, binary diffs or subagent reconstruction.
- Existing zero-based message/tool indexes are addresses; one-based labels are presentation. Call IDs are metadata, not globally unique addresses.
- Saved links resolve the current snapshot on a running explorer after unlock. Per-launch ports/credentials are not stable hosting; immutable revision recovery is outside scope.
- Proposed preview threshold: 20 lines or 2,000 characters, whichever comes first.
- Issue omits Alternatives and Governance fields: alternatives unspecified, no governance change proposed. Phase 3 follows architecture §§21–22 and ADR-014.
- Clarification scan found no blocking uncertainty across scope, data, identity, UX, security, dependencies or acceptance. These defaults await human approval.
