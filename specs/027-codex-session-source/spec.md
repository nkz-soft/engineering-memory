# Feature Specification: Codex session source

**Feature Branch**: `027-codex-session-source`
**Created**: 2026-11-03
**Status**: Draft for planning review
**Input**: Issue #28 — Add Codex sessions as a history source.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import and recall engineering history (Priority: P1)

An operator imports saved Codex sessions and retrieves their engineering decisions through the shared memory access surface.

**Why this priority**: Coding-agent work must enter the same memory bank as other history.
**Independent Test**: Import a synthetic session with a unique fact, then recall it filtered to Codex.
**Acceptance Scenarios**:
1. **Given** a supported saved session, **When** imported, **Then** its original and sanitized normalized conversation are archived and its memories carry `source:codex` and `codex:{session-id}` identity.
2. **Given** unchanged input, **When** imported again, **Then** extraction is skipped and no duplicate document is created.
3. **Given** an archived original, **When** replayed without the source file, **Then** the session can be parsed and imported again.

### User Story 2 - Preserve investigation evidence (Priority: P1)

An engineer recalls the command, failure, investigation and solution recorded in a session.

**Why this priority**: Prose alone loses the evidence explaining an engineering decision.
**Independent Test**: Normalize a synthetic command/error/fix session and inspect ordered text and associated tool requests/results.
**Acceptance Scenarios**:
1. **Given** tool calls and outputs, **When** normalized, **Then** their association and record order remain visible, including unsuccessful or unfinished calls.
2. **Given** a secret in tool arguments or output, **When** imported, **Then** the value is redacted before memory extraction or sanitized archive retrieval.
3. **Given** duplicate event representations of a message, **When** normalized, **Then** that message appears once.

### User Story 3 - Classify and recover across batches (Priority: P2)

An operator imports sessions from different working directories without manually assigning each project.

**Why this priority**: Explicit session context provides stronger evidence than mentioned paths.
**Independent Test**: Import two projects with an invalid session between them.
**Acceptance Scenarios**:
1. **Given** valid working-directory context, **When** classified, **Then** level-1 metadata classification takes precedence over prose aliases.
2. **Given** one malformed session, **When** processing a batch, **Then** it fails visibly and following sessions remain importable.

### Edge Cases

- Missing/conflicting identity or source timestamp fails the session; never invent identity or import-time dates.
- Empty directory produces no conversations; inaccessible input reports source unavailability.
- Truncated JSONL fails that snapshot; operators copy complete files before import.
- Unknown bookkeeping records do not become dialogue. Unsupported content-bearing records fail explicitly rather than silently losing history.
- No cwd uses existing alias/fallback classification; no filesystem or Git inspection is performed.
- Repeated session ids in a batch are rejected deterministically; symlinks are not followed.
- Compaction summaries and event mirrors must not duplicate original dialogue.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Read explicitly selected saved Codex session files or a directory of snapshots through the existing conversation-source boundary.
- **FR-002**: Preserve native identity, original times, source attribution and exact original bytes independently of extracted memory.
- **FR-003**: Preserve ordered textual messages, tool requests/results and non-text presence using the normalized model.
- **FR-004**: Apply the existing sanitization, classification, enrichment, archive, import-state and memory policies; sanitize context and tool fields as well as dialogue.
- **FR-005**: Use working-directory metadata for level-1 project detection without treating paths in dialogue/tool arguments as authoritative context.
- **FR-006**: Support unchanged skip, changed-content update, force, dry-run and archive replay with stable document identity.
- **FR-007**: Keep batch iteration usable after per-session format failures and expose safe error messages without conversation contents.
- **FR-008**: Expose explicit Codex source selection through the existing operator CLI, leaving its default unchanged.
- **FR-009**: Document the supported format subset and a separate source decision record; do not claim compatibility with every Codex version.

### Key Entities

- **Session snapshot**: Exact saved bytes, native session identity, source timestamps and working-directory/repository metadata.
- **Normalized conversation**: Ordered messages and tool evidence with stable Codex identity.
- **Import result**: Existing per-document status and provenance used for retries and replay.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every supported synthetic fixture passes the shared source contract suite.
- **SC-002**: A synthetic imported fact is recalled under the Codex source filter and its expected project, without matching another source.
- **SC-003**: Re-importing unchanged fixtures results in zero additional extraction calls; changed tool output updates the same document.
- **SC-004**: Every seeded secret is absent from outbound content and sanitized retrieval; archived originals remain replayable.
- **SC-005**: In a valid/invalid/valid batch, both valid sessions complete and exactly one format failure is reported.

## Assumptions

- Scope is Phase 2 coding agents (§22), not automated acquisition, live watching, or Codex configuration changes.
- Input is an operator-provided UTF-8 JSONL snapshot; directory import is nonrecursive. Operators can stage files from nested Codex storage into a flat input directory.
- Baseline dialect uses session metadata and response items; redundant event messages are not an alternate transcript. Event-only legacy histories require a future dialect.
- Session metadata cwd is authoritative for one session; later turn-local cwd does not silently move the entire conversation between projects.
- Forks with distinct native ids are distinct sessions; subagent aggregation, external tool-output files and encrypted reasoning are outside this feature.
- #19 is closed; Claude Code source #27 is merged and provides generic context classification. No unresolved product clarification is required.
