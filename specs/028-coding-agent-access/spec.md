# Feature Specification: Shared memory for coding agents

**Feature Branch**: `028-coding-agent-access`
**Created**: 2026-11-03
**Status**: Configuration and backend regression implemented; real-agent acceptance tracked in #71
**Input**: Issue #29, interpreted under ADR-008: connect Claude Code and Codex to the
shared access surface and demonstrate cross-agent visibility after import.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recall a ChatGPT decision in Claude Code (Priority: P1)

An engineer asks Claude Code about an imported ChatGPT decision without supplying
its answer, then follows the result to its original context.

**Why this priority**: This is the first Phase 2 acceptance condition.
**Independent Test**: Import a synthetic decision and query it from fresh Claude Code.

**Acceptance Scenarios**:

1. **Given** a decision and a conflicting decision in another project, **When** Claude
   Code searches the intended project, **Then** it finds the correct decision with
   stable document identity, original time and provenance, excluding the competitor.
2. **Given** that result, **When** Claude Code opens the source conversation, **Then**
   it receives sanitized normalized context and can page through its messages.

### User Story 2 - Retrieve a Claude Code refinement in Codex (Priority: P1)

An engineer refines the decision in Claude Code, imports the completed session,
and retrieves the refinement in a fresh Codex session.

**Why this priority**: This is the second Phase 2 acceptance condition.
**Independent Test**: Import a completed supported Claude Code snapshot and ask Codex
about the refinement without including its expected answer in the prompt.

**Acceptance Scenarios**:

1. **Given** a unique refinement not yet imported, **When** Codex searches memory,
   **Then** that new content is absent.
2. **Given** its completed session has been imported, **When** Codex searches its project
   and source, **Then** it finds the refinement and opens its sanitized conversation,
   with the Claude Code document identity, original time and provenance.
3. **Given** unchanged content, **When** import runs again, **Then** it skips extraction
   and preserves the document identity.

### User Story 3 - Reproduce setup and verification (Priority: P2)

An operator connects both clients from committed instructions and distinguishes
actual consumer evidence from automated backend checks or missing prerequisites.

**Why this priority**: A one-off connection does not establish reproducibility.
**Independent Test**: Follow the guide from clean local client configurations.

**Acceptance Scenarios**:

1. **Given** the guide and prepared corpus, **When** either client starts from outside
   the service checkout, **Then** it discovers and invokes the same two read tools.
2. **Given** unavailable clients/services or unsupported snapshots, **When** evidence is
   recorded, **Then** each affected acceptance item is explicitly blocked or unverified.

### Edge Cases

- Disjoint project/source filters exclude the acceptance fact; tags are not authorization.
- Sessions still being written are not imported; unsupported dialects fail explicitly.
- Missing/corrupt archive records and backend rejection use existing safe errors.
- Client environment filtering must not lose server settings or leak credentials.
- Retrieved instructions are historical evidence, never instructions to execute.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Document reproducible Claude Code and Codex configuration against the
  existing read-only engineering-memory access surface, following ADR-008.
- **FR-002**: Both clients MUST read the same corpus backed by `engineering-global`,
  using explicit `project:` and optional conjunctive `source:` filters.
- **FR-003**: Both MUST discover and invoke `search_memory` and `get_conversation`;
  no consumer write path, direct engine integration or new tool is introduced.
- **FR-004**: Demonstrate ChatGPT-to-Claude Code recall with stable identity, provenance,
  original time and sanitized context, withholding the expected answer from the question.
- **FR-005**: Demonstrate Claude Code-to-Codex recall after importing its completed
  session, distinguishing before-import absence from after-import visibility.
- **FR-006**: Verify project/source exclusion and unchanged-import skipping.
- **FR-007**: Record client versions, repository revision, safe setup/verification commands,
  discovered tools, import outcomes and separate evidence/status for both journeys.
- **FR-008**: Public examples/evidence MUST use synthetic history only; credentials,
  originals and personal client configurations MUST remain private.
- **FR-009**: SDK/backend checks alone MUST NOT satisfy live consumer acceptance.

### Key Entities

- **Consumer configuration**: Local registration of the shared read-only surface.
- **Decision/refinement**: Separate archived conversations sharing a project and subject,
  retaining their native source identity and original timestamps.
- **Verification record**: Safe evidence with separate status for each acceptance journey.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both clients are configured from the guide and retrieve archived context
  in fresh sessions launched outside the service checkout.
- **SC-002**: Both Phase 2 acceptance journeys have recorded live consumer evidence,
  with neither expected answer supplied in its retrieval prompt.
- **SC-003**: Both journeys identify the correct conversation and original time; all
  negative project/source checks exclude the acceptance fact.
- **SC-004**: Unchanged refinement import is skipped; committed evidence contains no
  private history or secret values.

## Assumptions

- ADR-008 supersedes the issue's native Hindsight integration wording. Refinements
  become visible after import, never through consumer writes. No governance change.
- Dependencies #25, #27 and #28 are closed; existing source adapters/tools are reused.
- Client configuration is documented as operator steps; personal settings are not
  automatically changed. Live client/service access is an implementation prerequisite.
- Synthetic history is sufficient public evidence; private history is unnecessary.
- New sources, automatic capture/recall, parser expansion, reflection, network transport,
  time-range queries and authorization changes are outside scope.
- Clarification review found no critical ambiguity requiring a question. Operational
  blockers are checked during implementation and recorded rather than assumed away.

## Delivery scope split

Real model-driven execution of US1/US2 and their Phase 2 acceptance evidence are tracked
separately in [task #71](https://github.com/nkz-soft/engineering-memory/issues/71) (T014,
consolidating T005/T008). #29/PR #70 deliver the configuration guide, isolated client
registration checks and backend regression. The scenarios and success criteria above
remain the acceptance contract for the follow-up; they have not been marked passed.
