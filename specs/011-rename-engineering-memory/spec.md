# Feature Specification: Rename to Engineering Memory

**Feature Branch**: `011-rename-engineering-memory`
**Created**: 2026-10-25
**Status**: Draft for human review
**Input**: Issue #48: adopt the consumer-independent project identity and prevent inherited consumer configuration from configuring this project.

## User Scenarios & Testing

### User Story 1 - Isolated configuration (Priority: P1)

As an operator starting the memory service from Hermes, I need the service to use its own configuration so inherited consumer settings cannot alter its behavior.

**Why this priority**: The current shared prefix creates a real configuration collision under the stdio process model.
**Independent Test**: Supply valid service configuration alongside conflicting and invalid consumer settings, then verify the service uses only its own settings.

**Acceptance Scenarios**:

1. **Given** valid service settings and conflicting consumer settings, **When** configuration loads, **Then** only service settings apply.
2. **Given** only settings under the former prefix, **When** required service configuration loads, **Then** loading fails safely instead of accepting consumer configuration.
3. **Given** an optional environment file, **When** configuration loads, **Then** the same isolation and existing environment-over-file precedence apply.

### User Story 2 - Consistent project identity (Priority: P2)

As a developer or operator, I can install, import, invoke and run the project under the Engineering Memory name consistently.

**Why this priority**: The name should express the shared store described by ADR-008 rather than imply a single-consumer plugin.
**Independent Test**: Install the project, run its command and container, and verify they expose the new identity.

**Acceptance Scenarios**:

1. **Given** a clean installation, **When** the public package and command are used, **Then** the new identity works and the command prints usage and the correct version.
2. **Given** the built container, **When** it runs without arguments, **Then** it exits successfully with usage and runs as an unprivileged user.
3. **Given** existing archived conversations, **When** the renamed project reads them, **Then** their identity, timestamps and content remain unchanged.

### User Story 3 - Discoverable project and guidance (Priority: P3)

As a contributor, I can find the renamed repository and follow documentation that uses one project name while identifying Hermes accurately as a consumer.

**Independent Test**: Review repository metadata and tracked guidance; follow the new repository URL and verify the former URL redirects.

**Acceptance Scenarios**:

1. **Given** project documentation, **When** its identifiers are audited, **Then** all identifiers naming this project use the new identity.
2. **Given** references to Hermes as a consumer, **When** the rename is complete, **Then** those references retain their meaning.
3. **Given** the former repository URL, **When** it is opened after the repository rename, **Then** it redirects to the new repository.

### Edge Cases

- Invalid or conflicting consumer-prefixed settings must not affect service configuration.
- Former-prefix values used explicitly as negative test inputs remain allowed and must be explained by their test context.
- A checkout directory retaining its former name must work; directory naming is not a configuration input.
- A non-editable installation must expose the same command and version as an editable one.
- Existing data directories, persisted identities and the shared memory bank must not be renamed.
- Repository rename permissions may be unavailable; report that external step separately rather than claiming completion.

## Requirements

### Functional Requirements

- **FR-001**: The project MUST use `engineering-memory` as repository, distribution and console-command identity and `engineering_memory` as its import identity.
- **FR-002**: Configuration MUST use the dedicated `ENGINEERING_MEMORY_` prefix, including nested settings and optional environment-file entries.
- **FR-003**: Former consumer-prefixed settings MUST have no effect; no compatibility fallback is provided.
- **FR-004**: Command help, version output, runtime service identifiers, container identity and CI image references MUST agree with the new name.
- **FR-005**: Tracked project documentation, examples, links, constitution and prior feature documents MUST use the new identity wherever they refer to this project, preserving consumer references.
- **FR-006**: ADR-008 MUST record the rename and configuration-collision rationale in one paragraph; no new decision record is required.
- **FR-007**: Existing archives, import state, document IDs, hashes, timestamps, tags and the shared bank MUST retain their semantics and locations.
- **FR-008**: The repository MUST be renamed and its former URL verified to redirect; incomplete external steps MUST be disclosed.
- **FR-009**: Existing behavior and security guarantees MUST remain covered by the full test suite and packaging checks.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every tested configuration path ignores consumer settings, including conflicting, invalid and former-prefix-only values.
- **SC-002**: Installation, command usage, command version and container smoke checks succeed under the new identity.
- **SC-003**: The identifier audit finds zero unexplained references naming this project with its former identity.
- **SC-004**: All existing regression checks and newly added rename checks pass, with recorded commands and results.
- **SC-005**: Both repository URLs reach the renamed project after the repository rename.

## Assumptions

- ADR-008 is merged in baseline commit `4ac75a3`; no open pull requests were reported when planning began.
- The proposed dedicated prefix is accepted as the default; no old-name import or command aliases are needed for this pre-release project.
- The local checkout folder may keep its name. Private data and operator environment files are never edited or committed.
- This is Phase 1 MVP work supporting architecture section 22 item 13, with no section 21 scope expansion or governance change.
- No critical ambiguities remain; implementation begins only after human review of this specification and plan.
