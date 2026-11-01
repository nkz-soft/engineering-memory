# Feature Specification: Import dry run

**Feature Branch**: `021-import-dry-run`
**Created**: 2026-11-01
**Status**: Draft — awaiting planning review
**Input**: Issue #22, Report a dry run without contacting Hindsight.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preview import decisions safely (Priority: P1)

An operator previews an export before spending extraction costs, seeing the identity,
project, original timestamp, redaction categories and intended action for each conversation.

**Why this priority**: Years of history must be inspectable before the first paid import.
**Independent Test**: Preview a synthetic corpus with a memory boundary that raises on every call.

**Acceptance Scenarios**:

1. **Given** new, changed and previously imported unchanged conversations, **When** a dry run
   completes, **Then** every valid conversation has the requested metadata and an explicit
   would-import or would-skip decision, with no memory-service calls.
2. **Given** secrets in synthetic input, **When** previewing, **Then** only category names appear;
   no original values, conversation bodies or titles appear in output or diagnostics.
3. **Given** missing or unavailable memory-service connectivity, **When** previewing local input,
   **Then** preview succeeds without constructing or contacting a memory client.

### User Story 2 - Preserve the subsequent real import (Priority: P1)

The operator previews without changing the next real run's decisions or durable history.

**Why this priority**: A preview must not cause real work to be skipped.
**Independent Test**: Snapshot archive and state, preview, then run a successful real import.

**Acceptance Scenarios**:

1. **Given** fixed input, configuration and initial state, **When** preview is followed by a
   successful real run, **Then** preview decisions match actual import/skip outcomes.
2. **Given** existing or absent local storage, **When** preview completes or fails, **Then**
   archive and import-state storage are unchanged, with absent storage remaining absent.
3. **Given** force reprocessing, **When** previewing, **Then** unchanged conversations would import.

### User Story 3 - Inspect partial and automated previews (Priority: P2)

The operator previews either an export or archived originals in text or structured output,
including recoverable failures without losing later valid conversations.

**Why this priority**: Preview belongs to the existing operational command surface.
**Independent Test**: Exercise both input selectors and output modes with malformed synthetic input.

**Acceptance Scenarios**:

1. **Given** an isolated malformed conversation, **When** previewing, **Then** a safe failed
   outcome appears and later conversations are processed; terminal reader errors remain distinct.
2. **Given** an empty input, **When** previewing, **Then** a successful empty summary is reported.
3. **Given** structured output, **When** preview completes, **Then** stdout contains exactly one
   structured result, clearly marked as a dry run, with intended counts rather than claimed writes.

### Edge Cases

- Missing state is empty without creating a database; corrupt/unreadable state fails safely.
- Repeated identities within a source follow the decisions of a successful sequential real run.
- Skipped items still receive preview metadata; metadata-stage failure is reported rather than hidden.
- Missing timestamps and project matches follow existing normalization and classification policy.
- Interruptions release source and state resources and do not write durable records.
- Remote retain, archive-write and state-write failures cannot be predicted by preview.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The existing import operation MUST expose dry-run mode for either existing input
  selector, with existing force and output options; source selection remains mutually exclusive.
- **FR-002**: Preview MUST parse, normalize, sanitize, classify and enrich each valid conversation,
  including items whose unchanged content would be skipped by real import.
- **FR-003**: Each valid preview row MUST show stable document id, project tag, original conversation
  timestamp, unique redaction categories, and would-import or would-skip decision.
- **FR-004**: Decisions MUST use the real import identity, pre-sanitization content hash and skip
  policy, including force behavior and sequential repeated-identity effects.
- **FR-005**: Preview MUST make zero memory-boundary calls, including setup/provision/read calls,
  and MUST NOT require reachable Hindsight or construct its client.
- **FR-006**: Preview MUST NOT create or alter archive or import-state storage, on success or failure.
- **FR-007**: Reports MUST distinguish intended actions from completed writes; failures use safe
  fixed categories, never raw exceptions, bodies, titles or secret values.
- **FR-008**: Preview MUST preserve per-conversation failure isolation, terminal source failure
  reporting, input order and the existing CLI exit-code policy.
- **FR-009**: The ordinary import, provisioning and status behaviors MUST remain compatible.

### Key Entities

- **Preview row**: Available conversation identity, project tag, original timestamp, redaction
  categories, intended action and optional safe failure stage.
- **Preview report**: Ordered rows, intended import/skip counts, failed count and terminal error.
- **Decision state**: Existing latest import records plus ephemeral effects of successful simulated
  imports, discarded after preview; never a second persistent source of truth.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every valid row in a synthetic mixed corpus contains all required metadata.
- **SC-002**: A fail-on-call memory boundary observes zero calls throughout every preview scenario.
- **SC-003**: Archive/state snapshots before and after preview are identical; absent paths stay absent.
- **SC-004**: Preview actions match 100% of actual import/skip outcomes in a subsequent successful
  run with the same inputs, starting state and configuration, including force and repeated ids.
- **SC-005**: Synthetic secret canaries appear zero times in captured stdout, stderr and logs.
- **SC-006**: Both sources, both output modes, empty input, isolated failures and terminal failures
  satisfy the documented command contract without regressing ordinary import.

## Assumptions

- Depends on #21 (feature 020), already merged into the feature base.
- Preview is read-only for all durable conversation storage, not merely for Hindsight.
- Default output is text; structured output follows the existing single-result convention.
- Redaction categories are unique and sorted, without matched values or snippets.
- Parity assumes unchanged inputs/configuration and successful real side effects; concurrent state
  changes and future remote failures are outside that guarantee.
- Existing settings validation remains; preview requires no live service or provisioning check.
- No new source, dependency, governance amendment or architecture scope expansion is needed.

## Clarification review

All functional, data, interaction, privacy, reliability, integration, edge-case, constraint,
terminology and completion categories are covered by the requirements and assumptions above.
No critical ambiguities remain; zero clarification questions required. Performance work is
limited to preserving conversation-by-conversation processing; no benchmark target is introduced.
