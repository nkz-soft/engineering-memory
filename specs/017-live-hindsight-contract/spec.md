# Feature Specification: Live Hindsight Contract

**Feature Branch**: `017-live-hindsight-contract`
**Created**: 2026-10-30
**Status**: Draft
**Input**: Issue #18 — Verify the Hindsight contract against a running instance.

## User Scenarios & Testing

### User Story 1 - Detect identity and retry regressions (Priority: P1)

A maintainer upgrading the memory engine needs evidence that re-import and retry cannot duplicate stored history or repeat extraction.

**Why this priority**: Identity and retry semantics protect both data integrity and extraction cost.
**Independent Test**: Run only identity/retry scenarios against a disposable live bank.

**Acceptance Scenarios**:
1. **Given** a retained conversation, **When** changed content is retained with its stable document identifier and omitted update mode, **Then** the replacement is retrievable and obsolete facts and duplicate documents are absent (§9–10).
2. **Given** an accepted asynchronous operation, **When** its identical request is repeated during processing and after completion, **Then** the original operation completes once and no second extraction is performed (§9).

### User Story 2 - Protect retrieval scope and time (Priority: P1)

A maintainer needs project filters and historical queries to keep returning the intended conversations.

**Why this priority**: Cross-project leakage and incorrect historical attribution silently undermine retrieval.
**Independent Test**: Run tag and temporal scenarios over synthetic conversations with known identities and dates.

**Acceptance Scenarios**:
1. **Given** documents with overlapping, disjoint and absent tags, **When** each supported consumer match mode is applied, **Then** returned document identities match an explicit inclusion/exclusion table (§6).
2. **Given** conversations with distinct original times imported in reverse chronological order, **When** historically scoped recall runs, **Then** dates and historical selection follow conversation time rather than import time (§9).
3. **Given** a bank never written, **When** recall is requested, **Then** the response is 404 and the read does not provision it (§9).

### User Story 3 - Gate upgrades automatically (Priority: P2)

A contributor needs the same checks to run automatically without access to private history or paid-service credentials.

**Why this priority**: Opt-in local experiments alone cannot catch upgrade regressions consistently.
**Independent Test**: Run the dedicated CI job with no repository secrets.

**Acceptance Scenarios**:
1. **Given** a pull request, **When** CI executes, **Then** the five contract families run against the pinned live engine with no silent skips.
2. **Given** unavailable services, failed extraction, timeout or a violated invariant, **When** the suite runs in CI, **Then** the job fails with the protected architecture section identified.

### Edge Cases

- Concurrent runs use distinct scratch banks and cannot touch engineering-global.
- Retain acceptance is insufficient: bounded completion polling precedes recall.
- Empty recall results cannot satisfy a filter or temporal test without a positive control.
- Cleanup runs after partial failures, with useful primary failure diagnostics preserved.
- Unsupported extraction requests fail explicitly instead of producing a false passing test.

## Requirements

### Functional Requirements

- **FR-001**: Verify default replace upsert and stable source-native document identity (§9–10), including absence of stale facts and duplicate documents.
- **FR-002**: Verify asynchronous operation-id replay during processing and after completion avoids repeated extraction (§9); synchronous retry is outside this guarantee.
- **FR-003**: Verify supported tag match modes using positive and negative document-identity assertions, including untagged documents (§6).
- **FR-004**: Verify per-item timestamp preservation and historically scoped recall with dates that differ from ingestion order (§9).
- **FR-005**: Verify never-written bank recall returns 404 without creating the bank (§9).
- **FR-006**: Execute all five families in CI against the repository-pinned real engine; an unavailable dependency, missing configuration, skip or contract mismatch fails the live job.
- **FR-007**: Identify the architecture section protected by every contract assertion and report bounded failures without credentials or private data.
- **FR-008**: Use only synthetic content in unique disposable banks; clean up after success and failure.
- **FR-009**: Preserve fast offline checks and document one reproducible local live-suite invocation.

### Key Entities

- **Contract scenario**: protected section, synthetic inputs, expected identities and observable outcome.
- **Scratch bank**: unique test-run resource, never an operator's bank.
- **Synthetic conversation**: stable source-native document id, facts, tags and original timestamp.
- **Extraction operation**: retry identity, processing/completion state and extraction invocation count.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every CI live run executes all five contract families without skips.
- **SC-002**: Each family has a negative control demonstrating that an incorrect result fails its assertions.
- **SC-003**: Two consecutive independent runs succeed without leftover scratch banks or identity collisions.
- **SC-004**: Contributors can reproduce the CI checks without private exports or paid-service credentials.

## Assumptions

- #16 and #17 are satisfied by main at 47d1a7a; this verifies the existing contract rather than redefining it.
- The engine's current pinned version is the initial baseline; no upgrade is bundled.
- A deterministic extraction fixture may replace only the LLM dependency in CI. Storage, async queue, tagging and recall remain real engine behavior. A paid-model quality benchmark is out of scope.
- Temporal grounding means original timestamps and historically scoped retrieval; generic relevance-ranked recall is not assumed to be chronologically sorted.
- The implementation will explicitly enumerate engine mode names corresponding to §6 terminology; unsupported or contradictory semantics fail rather than being silently reinterpreted.
- No governance change, new source, public API or production bank change is intended. No unresolved product clarification remains after review.
