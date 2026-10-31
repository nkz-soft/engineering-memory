# Feature Specification: Retry transient Hindsight failures

**Feature Branch**: `019-hindsight-retry`
**Created**: 2026-10-31
**Status**: Draft — awaiting planning approval
**Input**: Issue #20, "Retry transient Hindsight failures with backoff and jitter".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recover without duplicate extraction (Priority: P1)

As an importer operator, I want temporary memory service failures to recover automatically without submitting a different logical operation or paying for extraction twice.

**Why this priority**: A temporary refusal should not fail a conversation in a long import.
**Independent Test**: Stub two temporary failures followed by success and verify eventual completion with identical submission identity and content.

**Acceptance Scenarios**:

1. **Given** a retain submission receiving 503 twice, **When** the service recovers, **Then** submission succeeds after increasing randomized delays, using the same operation ID and payload throughout.
2. **Given** an acknowledged retain operation, **When** a status poll times out, **Then** the same status lookup is retried without resubmitting retain.
3. **Given** a recall receiving 429, **When** the service recovers within budget, **Then** the original query and scope produce the usual result.

### User Story 2 - Stop at permanent failures and finite limits (Priority: P1)

As an operator, I want invalid requests rejected immediately and an unavailable service to consume only a bounded retry budget.

**Why this priority**: Repetition must not hide invalid input or block the import indefinitely.
**Independent Test**: Count requests for permanent errors and continuous temporary failures using a controlled clock.

**Acceptance Scenarios**:

1. **Given** 400, 401 or 403, **When** a request fails, **Then** exactly one request occurs and a safe rejection reaches the caller.
2. **Given** persistent transient failure, **When** the attempt limit or operation deadline is reached, **Then** no further request is sent and a safe unavailable outcome reaches the caller.
3. **Given** invalid local input or an invalid successful response, **When** validation fails, **Then** validation is not retried.

### User Story 3 - Diagnose recovery safely (Priority: P2)

As an operator, I want structured attempt counts and outcomes so I can distinguish recovery from exhausted retries without revealing private data.

**Why this priority**: Recovery and failure must be observable in unattended imports.
**Independent Test**: Capture structured events for recovery, rejection and exhaustion with synthetic secret canaries in upstream diagnostics.

**Acceptance Scenarios**:

1. **Given** a request succeeding on attempt three, **When** its logs are inspected, **Then** attempts and final success are visible with correlation metadata.
2. **Given** secret canaries in a query, body, header and exception message, **When** any attempt fails, **Then** none of those values appear in logs or public errors.

### Edge Cases

- The remaining deadline cannot accommodate the next delay: stop without sleeping past it.
- A transient error becomes a permanent error: stop immediately at the permanent error.
- The connection resets after acceptance but before acknowledgement: reuse the original submission ID.
- Retry exhaustion leaves retain uncertain: preserve the existing in-process pending identity for a later identical call.
- Successful acknowledgement contains the wrong identity, or polling reports failed/cancelled/not_found: preserve existing semantics without treating these payloads as transport retry signals.
- Cancellation and programming errors propagate without retry.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Automatically retry only HTTP 429, 502, 503, 504, connection resets and request timeouts at the memory-store request boundary.
- **FR-002**: Never retry other HTTP failures, invalid input, invalid successful responses, terminal extraction failures or programming errors.
- **FR-003**: Preserve operation ID, document ID and serialized content across all attempts of one retain submission; preserve pending identity after uncertain exhaustion.
- **FR-004**: Use exponential backoff with jitter, a finite maximum delay and a finite attempt limit, all subordinate to the existing logical operation deadline.
- **FR-005**: Share the retain deadline across submission, polls and retries; do not reset it on each attempt. Recall retains its existing overall time budget.
- **FR-006**: Preserve existing memory interface signatures, safe error types, provenance, tag scoping and success semantics.
- **FR-007**: Emit structured per-request attempt and terminal outcome events, including attempt count and safe correlation fields, with no conversation content, queries, response bodies, credentials, headers or raw exception text.
- **FR-008**: Permit deterministic verification with stubbed transport, controlled timing and randomness, without a running engine or real sleeps.

### Key Entities

- **Logical operation**: One retain or recall, with a fixed deadline; retain has a stable submission identity and pending state.
- **Request attempt**: One submission, status lookup or recall request within that operation, with an attempt number and classified outcome.
- **Retry policy**: Allowed transient failures, delay schedule and attempt bound.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every allowed transient category recovers in a stubbed failure-then-success scenario; repeated submission payloads and identities are identical.
- **SC-002**: Every permanent-failure scenario makes exactly one attempt for the failing request.
- **SC-003**: Persistent failures stop within the configured attempt count and logical operation deadline, with zero requests after expiration.
- **SC-004**: Captured structured logs distinguish recovery, rejection and exhaustion and contain zero synthetic secret or conversation canaries.
- **SC-005**: Existing memory-store contract, pipeline isolation and identity guarantees remain verified by regression tests.

## Assumptions

- Issue #16's concrete memory store is available on current main; this feature changes its runtime retain, status polling and recall requests.
- Explicit bank provisioning and the synthetic smoke probe keep their existing behavior; automatic retries there are separate work.
- Default policy is four total attempts per request, starting with one second of backoff, capped at eight seconds with up to one second of additive jitter. Existing deadlines may stop earlier.
- No new CLI/environment options or persisted retry state are needed. Constructor-level policy/test seams are sufficient.
- Retry-After handling and durable cross-process retry coordination are outside scope.
- No critical ambiguities require formal clarification; these assumptions are reviewable at the planning gate.
