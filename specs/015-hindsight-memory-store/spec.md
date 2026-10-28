# Feature Specification: Hindsight Memory Store

**Feature Branch**: `015-hindsight-memory-store`
**Created**: 2026-10-28
**Status**: Draft — awaiting approval
**Input**: Issue #16, Implement the Hindsight memory store behind the interface.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retain and recall history (Priority: P1)

As an importer author, I retain a sanitized enriched conversation and retrieve its facts with original provenance through the existing memory boundary.

**Why this priority**: Enables subsequent import and retrieval work.
**Independent Test**: Retain a synthetic conversation and recall its distinctive fact.

**Acceptance Scenarios**:

1. **Given** a conversation with source, project and original time, **When** retained and recalled, **Then** results preserve provenance and stable document identity.
2. **Given** multiple projects, **When** recall requests one project's tags and a limit, **Then** only matching facts return within that limit.
3. **Given** no matching facts, **When** queried, **Then** the result is empty.

### User Story 2 - Retry and refresh safely (Priority: P1)

As an operator, I can retry uncertain delivery and replace grown conversations without duplicates or repeated extraction for the same operation.

**Why this priority**: Replay must preserve history and avoid repeated extraction costs.
**Independent Test**: Replay after an uncertain outcome, then replace changed content.

**Acceptance Scenarios**:

1. **Given** uncertain delivery, **When** retried as the same operation, **Then** extraction is not charged twice and one logical document remains.
2. **Given** retained content, **When** updated, **Then** replacement preserves identity and removes stale content.

### User Story 3 - Preserve oversized conversations (Priority: P2)

As an operator, I can retain long discussions without losing text or exposing delivery parts as separate documents.

**Why this priority**: Long discussions carry important engineering context.
**Independent Test**: Force multipart delivery with a small threshold and recall facts from both ends.

**Acceptance Scenarios**:

1. **Given** an oversized conversation, **When** retained, **Then** all text remains ordered under one document identity.
2. **Given** a previously retained oversized conversation, **When** refreshed or retried, **Then** no old tail or duplicate delivery parts remain.

### Edge Cases

- Empty content and invalid limits are rejected explicitly.
- Single oversized messages and multibyte text split without loss.
- Timeout and retryable failures remain distinguishable from rejected input or unauthorized access.
- Missing or malformed provenance fails explicitly rather than inventing values.
- Several facts may legitimately belong to one document; tests do not demand exactly one recalled fact.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Implement the existing memory boundary without exposing engine types to callers.
- **FR-002**: Retain a conversation as one logical document with its existing deterministic identity.
- **FR-003**: Preserve original conversation time, full provenance and tags on all delivery parts; never substitute import time.
- **FR-004**: Reuse retry identity for uncertain delivery and replace changed content without duplicates; deliberate fresh extraction remains possible.
- **FR-005**: Preserve all serialized text in order during multipart delivery and replacement.
- **FR-006**: Recall supports strict tag scoping, limits, typed provenance and empty matches.
- **FR-007**: Map failures to existing permanent/transient boundary errors without exposing content, credentials or response bodies.
- **FR-008**: Enforce engine implementation isolation through production import-graph checks.
- **FR-009**: Accept sanitized enriched input; archiving and sanitization remain pipeline prerequisites.
- **FR-010**: Verify required behavior on the pinned running engine, including retry idempotency and multipart replacement.

### Key Entities

- **Enriched conversation**: Conversation, provenance and tags with derived stable identity.
- **Logical operation**: Intended delivery whose retries share identity; distinct from a deliberate fresh delivery.
- **Delivery part**: Ordered fragment of one logical document, invisible to callers.
- **Recall result**: Matching fact with original provenance and optional relevance score.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All reusable memory contract scenarios pass for the concrete store.
- **SC-002**: Retrying the synthetic operation leaves one logical document and causes no second extraction for that operation.
- **SC-003**: Multipart delivery preserves 100% of serialized text and recalls facts from both ends with one document identity; refresh removes stale content.
- **SC-004**: Every result in provenance and scoping scenarios has the expected project and source.
- **SC-005**: No production module outside the implementation imports engine-specific implementation code, directly or transitively.

## Assumptions

- Phase 1 MVP only; no new source, consumer, bank strategy or dependency choice.
- Issues #9 and #15 are closed prerequisites; closure does not prove live engine verification.
- The shared bank and mission are provisioned separately (#17); no provisioning in this store.
- Retry/backoff orchestration and durable import state remain #20. This adapter preserves pending operation identity within its lifecycle; durable cross-process retry coordination is a documented integration limitation.
- Only synthetic history is used for verification.
- Architecture and pinned-engine contract discrepancies require explicit reconciliation before implementation can be declared complete.
