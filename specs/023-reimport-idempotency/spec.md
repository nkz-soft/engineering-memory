# Feature Specification: Prove re-import idempotency

**Feature Branch**: `023-reimport-idempotency`
**Created**: 2026-11-01
**Status**: Draft
**Input**: Issue #24, "Prove a re-import creates no duplicates".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Replay unchanged history safely (Priority: P1)

As an operator, I can repeat an import without duplicate documents or repeated extraction work.

**Why this priority**: Routine replay must be safe and free of redundant extraction.
**Independent Test**: Import a small synthetic corpus, repeat unchanged, and compare recalled identities and extraction activity.
**Acceptance Scenarios**:

1. **Given** a successfully imported corpus and its import state, **When** the same corpus is imported again, **Then** every conversation is skipped, no retain submission or extraction occurs, and recall returns exactly the original document identities.

### User Story 2 - Recover after import-state loss (Priority: P1)

As an operator, I can replay history after losing local import state without duplicating memory documents.

**Why this priority**: Importer bookkeeping alone cannot protect recovery or imports from another machine.
**Independent Test**: Import the corpus, close and remove only the temporary state store, then replay against the same memory bank.
**Acceptance Scenarios**:

1. **Given** an imported corpus whose local state is deleted, **When** it is imported again, **Then** every conversation is submitted under its original stable identity and recall still exposes exactly one document identity per conversation.

### User Story 3 - Submit only changed history (Priority: P2)

As an operator, I can update one conversation without reprocessing unrelated history.

**Why this priority**: Selective updates preserve correctness while bounding extraction work.
**Independent Test**: Import at least two conversations, edit one while preserving source identity, and replay with state intact.
**Acceptance Scenarios**:

1. **Given** an imported corpus with one changed conversation, **When** it is imported again, **Then** only that conversation is submitted, its updated fact is recalled under the same identity, and unchanged documents retain their original facts.

### Edge Cases

- Recall returning nothing or omitting a corpus member must fail, rather than passing an empty-set comparison.
- A conversation may yield multiple facts: document cardinality counts distinct document identities, not fact rows.
- Truncated recall cannot certify completeness; use a deliberately small corpus and per-conversation queries with ample result budgets.
- State-loss and changed-content cases use independent initial imports so one case cannot accidentally invalidate another's preconditions.
- Missing Docker or unhealthy services fail the required live gate; offline runs may explicitly skip live tests.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Verify all three scenarios against a live memory engine using real import orchestration and persistence adapters.
- **FR-002**: Use at least two synthetic conversations with independently defined source identities and distinguishable facts.
- **FR-003**: Assert baseline and replay document identities from recall, independently of import-state counters.
- **FR-004**: Unchanged replay with intact state must perform zero submissions and zero additional extraction calls.
- **FR-005**: State-loss replay must demonstrate actual resubmission of all corpus members and stable, duplicate-free recalled document identities.
- **FR-006**: Changed-content replay must submit exactly the changed identity, recall its updated fact and preserve other documents.
- **FR-007**: Preserve original and sanitized archive records, stable provenance, and existing bank and tag conventions.
- **FR-008**: Required live validation must reject missing, skipped, failed or errored scenario results, with bounded execution and isolated cleanup.
- **FR-009**: Provide negative controls proving assertions detect missing documents, unexpected identities, redundant submissions/extraction and failure to submit the changed identity.

### Key Entities

- **Corpus**: Synthetic conversations with stable source identifiers, original times and distinguishable decisions.
- **Run evidence**: Expected and observed submitted identities, extraction-call delta and imported/skipped/failed totals.
- **Recall evidence**: Facts grouped by stable document identity, including expected original or updated decisions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Unchanged replay produces zero additional extraction calls and zero additional documents.
- **SC-002**: Recovery replay submits every corpus member and preserves exactly the baseline document identity set.
- **SC-003**: A one-conversation edit causes exactly one submission and exposes the updated decision with no extra documents.
- **SC-004**: All three required live scenarios pass with no skips; deliberately invalid evidence fails its corresponding assertion.

## Assumptions

- Dependency #23 is complete and merged into the base branch.
- "No extraction paid for twice" applies to unchanged replay with intact state. State-loss recovery proves identity upsert; it does not promise avoiding extraction after bookkeeping loss.
- Credential-free deterministic extraction against the real engine is sufficient for this correctness gate; real-model retrieval quality is separate evaluation work.
- This is Phase 1 item 8 and architecture section 17; no new source, production interface, bank strategy or governance change is intended.
- No critical ambiguities require human clarification. Service details and assertion mechanics are resolved in planning.
