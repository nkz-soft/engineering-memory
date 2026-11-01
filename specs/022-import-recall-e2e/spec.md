# Feature Specification: Import and recall end to end

**Feature Branch**: `022-import-recall-e2e`
**Created**: 2026-11-01
**Status**: Draft
**Input**: Issue #23 — import a synthesized conversation and retrieve its engineering decision with provenance, tags and original time intact.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retrieve an imported decision (Priority: P1)

As a maintainer, I need evidence that an ordinary import produces a recallable engineering decision, rather than merely accepting a write.

**Why this priority**: Individually passing components cannot prove the assembled system works.
**Independent Test**: Import one synthetic conversation into an empty isolated store and query for its known decision.

**Acceptance Scenarios**:

1. **Given** an empty isolated store and a synthetic conversation with a known engineering decision, **When** the ordinary import completes and a related query runs, **Then** at least one result contains the expected decision and refers to that conversation.
2. **Given** that result, **When** its provenance is checked, **Then** source, native identifier, original timestamp, project, known repository and importer version match independently specified expected values.
3. **Given** the imported conversation's required tags, **When** matching and disjoint scope queries run, **Then** matching scopes retrieve the decision and disjoint scopes exclude it.
4. **Given** the stored fact, **When** its temporal grounding is inspected, **Then** it uses the original conversation date rather than the import date.

### User Story 2 - Detect assembled-system regressions in review (Priority: P1)

As a reviewer, I need the automated gate to fail when the decision or its identifying context is lost.

**Why this priority**: An unexecuted or silently skipped test cannot protect a release.
**Independent Test**: Execute the required live gate and inspect the result; repeat with deliberate field omissions.

**Acceptance Scenarios**:

1. **Given** the automated gate's supported environment, **When** it runs, **Then** the end-to-end case executes without skips and passes.
2. **Given** a missing decision, provenance field, required tag or original timestamp, **When** validation runs, **Then** it fails with a diagnostic naming the violated expectation.
3. **Given** an unavailable or failing live dependency, **When** the required gate runs, **Then** it fails within a bounded deadline rather than reporting success.

### Edge Cases

- A previously populated store must not supply the expected result: use a fresh isolated bank and empty local state for each run.
- Extraction completion and retrieval have bounded waits; no unbounded retries.
- Cleanup runs after assertion failures and removes only test-owned resources.
- Local default tests may skip live cases explicitly; required CI execution must reject skips and missing cases.
- Historical fixture timestamps differ from today's date so import-time substitution is detectable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Exercise the real source parser, sanitizer, classifier, enrichment, local archive, persistent import state, ingestion orchestration and memory adapter against the live memory engine.
- **FR-002**: Use only synthesized conversations with a known decision and independently defined expected context.
- **FR-003**: Assert decision content and complete provenance on recalled results; write acknowledgement alone is insufficient.
- **FR-004**: Verify every required tag's presence and retrieval behavior, including disjoint-scope exclusion.
- **FR-005**: Verify original time both as provenance and as the live fact's temporal grounding.
- **FR-006**: Verify original and sanitized normalized archive records exist and successful import state is recorded.
- **FR-007**: Provide required automated live execution, bounded startup/test deadlines and failure-safe resource cleanup.
- **FR-008**: Demonstrate the assertions reject omitted provenance, tags and timestamps without changing production contracts.

### Key Entities

- **Synthetic conversation**: Stable source identity, historical creation date, known engineering decision, project and repository cues.
- **Expected evidence**: Independently authored decision terms, provenance values and complete required tag set.
- **Run resources**: Empty archive and import-state paths plus a disposable isolated test bank.
- **Recalled fact**: Decision content and provenance, related to the persisted conversation by stable identity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One clean run retrieves the known decision with all expected provenance fields and tags intact.
- **SC-002**: Each deliberate omission of a required provenance field, tag or timestamp causes validation failure.
- **SC-003**: Required automation reports zero skipped or missing end-to-end cases and returns failure on dependency failure.
- **SC-004**: Two successive clean runs succeed independently and leave no test bank or persisted test data behind.

## Assumptions

- Scope is ARCHITECTURE §22 Phase 1 item 11; no access-surface feature, new source, memory contract or governance change is introduced.
- Dependencies #18 and #21 are available in the current base (live contract and operator CLI).
- Deterministic synthetic extraction is appropriate for the required credential-free CI gate; this proves orchestration and retrieval, not real-model extraction quality.
- The existing pinned isolated live stack and mission are reused, with testcontainers lifecycle management added for this gate.
- Scratch banks are test-only isolation; production continues using engineering-global.
- No critical ambiguity requires a user question; infrastructure details are settled in planning.
