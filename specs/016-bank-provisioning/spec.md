# Feature Specification: Bank Provisioning

**Feature Branch**: `016-bank-provisioning`
**Created**: 2026-10-30
**Status**: Draft — awaiting human plan review
**Input**: Issue #17, Provision the bank and configure its retain mission.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prepare the shared bank (Priority: P1)

As an operator, I can explicitly prepare the shared engineering bank before importing history, so extraction starts with the intended priorities.

**Why this priority**: Provisioning is a prerequisite for the first import.
**Independent Test**: Start with a missing disposable bank; provision it and read back the exact mission.
**Acceptance Scenarios**:
1. **Given** a bank whose read returns 404, **When** provisioning succeeds, **Then** the bank exists and its mission matches Architecture §12 verbatim.
2. **Given** a provisioned bank, **When** the operator provisions it again, **Then** the operation succeeds with the same mission and no added memories or changed unrelated settings.

### User Story 2 - Evolve extraction priorities (Priority: P2)

As an operator, I can reapply an updated project mission without deleting existing memories.

**Why this priority**: Extraction policy must evolve without losing history.
**Independent Test**: Apply a revised synthetic mission in an isolated test; confirm exact read-back and preservation of existing data.
**Acceptance Scenarios**:
1. **Given** an older mission and existing memories, **When** the current project mission is applied, **Then** the mission is replaced and existing memories remain unchanged.
2. **Given** successful provisioning, **When** the operator reads the documentation, **Then** it explains that changes affect future extraction and re-extraction requires the separate archive replay workflow.

### Edge Cases

- Unavailable engine, invalid credentials, timeout, malformed response, or mismatched read-back: fail with a bounded, sanitized diagnostic and no success report.
- Interrupted creation/configuration: a subsequent invocation converges to the desired mission.
- Existing bank with other configuration: preserve unrelated settings and memories.
- Failed verification after a write: report failure; do not delete or roll back the bank.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Provide an explicit operator provisioning command before import; do not provision implicitly on reads or retention.
- **FR-002**: Use the existing configured bank, defaulting to `engineering-global`; production follows the single shared bank policy.
- **FR-003**: Create a missing bank without inserting synthetic conversation memories.
- **FR-004**: Apply the complete Architecture §12 mission verbatim, including both priority sections, as bank configuration.
- **FR-005**: Read configuration back and verify the exact mission before reporting success.
- **FR-006**: Repeated provisioning MUST succeed without duplicates, memory extraction, unrelated configuration changes, or deletion of existing data.
- **FR-007**: Reapplication MUST replace an older mission with the current project mission; document that this affects future extraction only.
- **FR-008**: Fail within a bounded time with safe diagnostics on configuration, transport, permission, or verification failures; never expose tokens, response bodies, or conversation contents.
- **FR-009**: Verify missing-bank, mission round-trip and repeated-run behavior against the pinned self-hosted engine using disposable test banks.

### Key Entities

- **Shared bank**: Existing configured persistent destination for all projects; project separation stays tag-based.
- **Retain mission**: Version-controlled extraction priorities from Architecture §12; a bank-level policy, never a per-conversation field.
- **Provisioning result**: Verified success or safe failure; no new history identity or import-state record.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A disposable bank returns 404 before provisioning and is readable with an exact mission match afterwards.
- **SC-002**: Two consecutive runs succeed and leave equal mission configuration, equal memory count and unchanged unrelated settings.
- **SC-003**: Replacing an older mission produces an exact current-mission match while preserving all seeded synthetic memories.
- **SC-004**: All tested transport, permission and verification failures return non-success without secret-bearing diagnostics.

## Assumptions

- Scope is Phase 1 MVP, architecture §§21–22; #16 is merged and supplies the engine adapter and HTTP conventions. #18 and #21 consume this prerequisite later.
- The command uses existing settings; no arbitrary mission input or per-item mission parameter is added. Mission evolution means editing the version-controlled mission and rerunning provisioning.
- Default production bank stays `engineering-global`; tests explicitly use uniquely named disposable banks.
- No retroactive extraction, importer orchestration, new history source, dependency or decision-record change belongs to this feature.
- Clarification review found no critical ambiguities; implementation details are resolved in the plan and pinned integration tests.
