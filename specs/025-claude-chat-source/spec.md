# Feature Specification: Claude chat history source

**Feature Branch**: `025-claude-chat-source`
**Created**: 2026-11-02
**Status**: Draft
**Input**: Issue #26 — Add Claude chats as a history source.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import Claude conversations (Priority: P1)

As the operator, I can import my Claude plain-chat export through the existing import workflow,
so the engineering history I kept there becomes searchable with my ChatGPT history.

**Why this priority**: Half the history is currently inaccessible.
**Independent Test**: Import synthetic Claude conversations and verify archived originals,
normalized text, original times and stable `claude-chat:` identities.

**Acceptance Scenarios**:

1. **Given** a supported Claude export, **When** it is imported, **Then** each readable conversation
   preserves its native identity, title, message order, roles, text and available original times.
2. **Given** the same export imported twice, **When** it is imported again unchanged, **Then**
   conversations are skipped without another extraction or duplicate memory.
3. **Given** a malformed conversation between valid ones, **When** importing, **Then** that record
   fails safely and subsequent valid conversations are processed.

### User Story 2 - Recall Claude history beside ChatGPT (Priority: P1)

As a memory consumer, I can find facts from both sources, filter by `source:claude-chat`, and open
sanitized Claude conversations using the same read surface.

**Why this priority**: Import is useful only when the history can be retrieved.
**Independent Test**: Import distinct synthetic facts from both sources and verify unfiltered and
source-filtered recall, including opening a Claude conversation.

**Acceptance Scenarios**:

1. **Given** both sources contain a known fact, **When** recall is filtered to Claude chats,
   **Then** only Claude results match, carrying `source:claude-chat` provenance.
2. **Given** a Claude conversation containing a synthetic secret, **When** recalled or opened,
   **Then** the secret is redacted while the surrounding engineering context remains.

### User Story 3 - Preview and replay Claude imports (Priority: P2)

As the operator, I can preview Claude imports without writes or extraction, and replay archived
originals without downloading another export.

**Why this priority**: Existing operational guarantees must hold for every added source.
**Independent Test**: Preview an export with a fake memory boundary that refuses calls; then
remove the export and replay from its archived originals.

**Acceptance Scenarios**:

1. **Given** a Claude export, **When** dry-run is requested, **Then** decisions are reported without
   writing archive/state or contacting the memory engine.
2. **Given** only archived Claude originals remain, **When** replayed with force, **Then** the same
   normalized conversation is reconstructed and passes the shared sanitization path.

### Edge Cases

- Empty exports yield no conversations; missing files report an unavailable source.
- Missing native identifiers or invalid/missing conversation time fail that conversation; import
  time and generated identifiers are never substituted.
- Duplicate conversation identifiers within one export fail the later occurrence.
- Missing optional titles/message times remain absent. Equal times do not reorder messages.
- Unsupported content is represented explicitly as non-text rather than silently lost; no
  attachments are fetched. Original records retain unrecognized fields for future replay.
- Structurally invalid export framing is terminal; recoverable individual record errors are not.
- Claude Code logs and unrelated files are rejected as unsupported input.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST import Claude plain-chat exports with the existing import command and
  receive the existing summary, exit-code and per-conversation failure behavior.
- **FR-002**: Claude conversations MUST use their native identifier, `claude-chat:{id}` document
  identity, original times and `source:claude-chat` tag; identity MUST be stable across runs.
- **FR-003**: Normalization MUST preserve ordered human/assistant turns and text exactly, mapping
  source roles to the existing role vocabulary without treating import time as history time.
- **FR-004**: Both original and sanitized normalized forms MUST be archived through the existing
  pipeline; archive-only replay MUST reconstruct the conversation from the original record.
- **FR-005**: The source MUST satisfy the existing conversation-source contract, including repeatable
  reads, empty input, source consistency and iteration after recoverable record errors.
- **FR-006**: Secrets MUST pass through the existing sanitizer before memory retention or access;
  diagnostics MUST NOT contain conversation contents, secret values or refused input values.
- **FR-007**: Unchanged re-imports MUST skip extraction using existing identity/hash policies.
- **FR-008**: Recall MUST support mixed-source results and existing source filtering without changes
  to the memory store or access surface.
- **FR-009**: Dry-run and force behavior MUST remain available for Claude export and archive input.
- **FR-010**: Runtime changes MUST be confined to the new Claude chat source and its selection/
  registration. Shared domain, pipeline, sanitizer, classifier, archive, state, memory and access
  policies MUST remain unchanged. Tests, source-selection help and the required ADR are in scope.
- **FR-011**: The supported export shape, normalization decisions, unsupported content policy and
  alternatives MUST have a dedicated source decision record before implementation is merged.

### Key Entities

- **Claude export**: A local bundle containing plain-chat conversation records.
- **Claude conversation**: Native id, optional title, creation/update times and ordered messages.
- **Source conversation**: The existing pair of normalized conversation and original record bytes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every valid synthetic conversation in the acceptance corpus imports with the expected
  text, order, original times and native identity; every malformed record is reported separately.
- **SC-002**: A second unchanged import produces zero new extractions and zero duplicate documents.
- **SC-003**: A mixed-source recall finds the known Claude and ChatGPT facts; a Claude source filter
  excludes all ChatGPT fixtures and opens the correct sanitized conversation.
- **SC-004**: Preview produces zero writes and zero memory calls; archive-only replay reproduces
  all supported normalized fixture conversations without their export files.

## Assumptions

- Issue #19's shared pipeline is available on main; no new pipeline is needed.
- Input is the operator's downloaded Claude plain-chat export, not a live API or Claude Code log.
- Initial support targets the documented fixture shape; future incompatible export versions require
  explicit parser work. No private history is committed to establish examples.
- Plain text is indexed. Binary attachments and opaque blocks remain in originals and have explicit
  non-text markers where representable; they are not uploaded or fetched separately.
- Existing classification handles missing project information as `project:unknown`.
- Source selection may require a small explicit option at the existing CLI composition boundary;
  existing invocations retain their ChatGPT default.
- Clarification review found no blocking product ambiguity; export-schema evidence and mapping are
  technical planning responsibilities, with uncertainty explicitly recorded in research.
