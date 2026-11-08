# Feature Specification: Verify Reflect on the Accumulated Corpus

**Feature Branch**: `032-verify-reflect`
**Created**: 2026-11-08
**Status**: Draft
**Input**: [Issue #31](https://github.com/nkz-soft/engineering-memory/issues/31)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare synthesis with lookup (Priority: P1)

A memory operator compares what the two operations deliver for identical questions on the accumulated bank and determines where synthesis justifies its latency.

**Why this priority**: The value of synthesis on years of engineering history is the question this feature needs to answer.

**Independent Test**: Run both operations on a fixed set against the same bank and reproduce the comparison from the evaluation records.

**Acceptance Scenarios**:

1. **Given** a populated bank and a frozen set of questions with reviewed expectations, **when** both operations receive the same question and project scope, **then** the operator can compare coverage of expected points, grounding, latency, and failures for each pair.
2. **Given** an evolution question, **when** synthesis relates evidence from multiple conversations in the correct order, **then** the review distinguishes that contribution from merely returning matching facts.
3. **Given** incomplete evidence, an unsupported claim, or an operation failure, **when** the operator reviews a pair, **then** the comparison records that outcome separately and keeps it visible in the totals.

### User Story 2 - Choose an operation as a consumer (Priority: P2)

A coding agent or other consumer uses lookup for ordinary questions and can request project-scoped synthesis through the shared memory surface.

**Why this priority**: The comparison is actionable only if consumers know when and how to call each operation.

**Independent Test**: Follow the consumer guide for one direct lookup and one synthesis question and check the returned evidence against sanitized history.

**Acceptance Scenarios**:

1. **Given** a question about the evolution of a project decision, **when** a consumer requests synthesis for that project, **then** it receives an answer with supporting conversation references when validated evidence is available.
2. **Given** an ordinary lookup or an unsupported synthesis answer, **when** the consumer follows the guide, **then** it uses lookup to retrieve evidence and can open the supporting sanitized conversations.

### Edge Cases

- Missing provenance is excluded from supporting references. Withhold the answer and report insufficient evidence if no reference validates or evidence belongs to another project.
- Conflicting or superseded decisions are scored against their source chronology. A plausible but unsupported conclusion is recorded explicitly.
- An unavailable or empty accumulated bank prevents a live conclusion. Synthetic checks can validate the procedure.
- Private questions, answers, conversation identifiers, and diagnostics stay local. Published comparisons contain only reviewed, non-identifying summaries.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Freeze questions, project scopes, expected points, and supporting evidence before running either operation. Include evolution and decision synthesis questions, plus ordinary lookup controls.
- **FR-002**: Compare both operations with identical question text and scope on one stable bank. Record configuration, elapsed time, and outcome for every attempted pair.
- **FR-003**: Review expected-point coverage, cross-conversation synthesis, chronology where applicable, and unsupported claims against sanitized sources. Keep coverage of retrieved evidence distinct from quality of a generated answer.
- **FR-004**: Publish a privacy-reviewed comparison with scope, sample size, results, missing evidence and failures, limits, and a rule for choosing between operations.
- **FR-005**: Provide read-only project-scoped synthesis on the shared memory surface. Expose only archive-validated references and withhold answers when no reference validates.
- **FR-006**: Document the invocation and routing rule for consumers, including how to follow up on insufficient evidence.

### Key Entities

- **Evaluation case** — opaque case ID, project scope, question type, prompt, expected points, and local source evidence.
- **Paired result** — two operation outcomes with timing and a reviewer assessment of coverage and grounding.
- **Synthesis answer** — generated text and validated references to supporting sanitized conversations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Attempt at least six synthesis pairs, split between evolution and decision synthesis, and at least two lookup control pairs on the accumulated bank. Report every attempted pair and its outcome.
- **SC-002**: For every completed synthesis pair, report expected-point coverage for both operations and mark whether synthesis added a supported relationship across at least two conversations, made unsupported claims, or yielded insufficient evidence.
- **SC-003**: Publish measured elapsed times with sample counts and explain which results support the routing rule and where the evidence is inconclusive.
- **SC-004**: Verify that the consumer can request synthesis on the shared surface, that returned references can be opened there, and that requests without validated evidence return a distinguishable outcome.

## Assumptions

- The live run uses an authorized local accumulated bank with #30's project models where available. Record model availability and the date range without identifying projects or sources publicly.
- The proposed case counts are a practical minimum for a qualitative comparison. The #32 synthetic benchmark remains a repeatable lookup baseline and its data format can inform the private case set.
- Use manual grounding review so paraphrases, contradictory evidence, and chronology can be judged against the sources. The experiment can conclude that reflect adds little value on the tested questions.
