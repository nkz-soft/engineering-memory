# Feature Specification — Source-Backed Decision History

**Feature Branch** `039-decision-history-timeline`  
**Created** 2026-11-16  
**Status** Draft for approval  
**Input** [Issue #85](https://github.com/nkz-soft/engineering-memory/issues/85), Phase 3 synthesis and evaluation. The standing decisions model gives a snapshot. Operators need to understand when a decision changed and what prompted it.

## User Scenarios & Testing

### User Story 1 — Follow a decision across sessions (P1)

The local explorer operator enters a project and a decision topic, then opens its history to see the original decision, what replaced it and the documented reason for the change.

**Why this priority** The current snapshot alone cannot explain a change.

**Independent test** Use synthetic sessions in which a project adopts configuration A, revises it and later explicitly replaces it with B. Use another project with the same topic to test isolation.

1. Given the sessions above, when the operator opens the history, then the detail shows both versions, the documented reasons and the distinct proposal, adoption, revision and replacement events supported by the messages.
2. Given the other project's matching topic, when the operator opens the history, then none of that project's messages appear.
3. Given only a proposal, when the operator opens the history, then the proposal appears and its acceptance remains unknown.

### User Story 2 — Inspect chronology and disagreement (P1)

The operator sees where evidence is incomplete or competing accounts remain unresolved.

**Why this priority** An apparent date or resolution can change a reader's understanding of the decision.

**Independent test** Use a dated session, an undated amendment and two incompatible, unresolved claims.

1. Given usable message times, when the detail opens, then dated events appear oldest first. Events with missing or ambiguous times remain visible with an explanation. Equal times give an explicit ordering caveat.
2. Given incompatible accounts without an evidenced resolution, when the detail opens, then it labels the conflict as unresolved and shows both accounts with their own evidence.

### User Story 3 — Open the evidence (P1)

The operator opens the exact archived message behind a timeline event or competing account.

**Why this priority** The archived exchange lets the operator judge the summary in context.

**Independent test** Open citations in different sessions, including an undated message, and repeat after making one citation unavailable.

1. Given a visible event, when the operator selects its source, then the explorer opens the corresponding sanitized message in context and highlights the cited evidence.
2. Given that the source cannot be resolved at click time, when the operator selects it, then the explorer shows an unavailable-source state.

### Edge Cases

- Empty history, limited coverage and inability to verify evidence have distinct states.
- A later disagreement alone leaves the earlier decision's disposition open.
- Missing message times stay unknown. A conversation start, import time or generated date cannot establish an event time.
- Changing project scope or locking the explorer clears the previous result. Late responses cannot repopulate it.

## Requirements

### Functional Requirements

- **FR-001** The authenticated local explorer MUST offer a decision detail view for one explicit project and one decision topic per lookup.
- **FR-002** The detail MUST show supported proposals, adoptions, revisions and supersessions. For a supported supersession, it MUST identify both versions, provide evidence for the change and show the reason when the source states one.
- **FR-003** Every event MUST have a source that identifies the archived message supporting the action. Additional context can have separate citations. Selecting the event's source MUST open that message.
- **FR-004** The detail MUST order events with known times by their action messages' timestamps. It MUST visibly flag equal-time ambiguity and show events whose times are unknown or disputed without assigning them an invented position in the dated sequence.
- **FR-005** The detail MUST expose unresolved conflicts and link each competing account to its own archived message. It MUST represent incomplete coverage or ambiguous outcomes explicitly.
- **FR-006** Content MUST be read-only, project-scoped and sanitized. Results MUST clear on project change, a new lookup or locking. Error states MUST avoid exposing private content from rejected sources.

### Key Entities

- **Decision detail** — the requested topic and project, supported events, unresolved conflicts and evidence coverage.
- **Decision event** — one evidenced lifecycle action, decision version, documented reason when available, source and chronology.
- **Conflict** — incompatible accounts with individually inspectable evidence and unresolved status.
- **Message evidence** — a source message and the relevant text within it.

## Success Criteria

### Measurable Outcomes

- **SC-001** A synthetic cross-session supersession shows both decisions, all four evidenced lifecycle actions, the documented reason for replacement and zero messages from a matching foreign project.
- **SC-002** A mixed-time fixture shows its dated events in chronological order and visibly marks every undated, disputed or equal-time ordering case. Every seeded unresolved competing account is independently inspectable.
- **SC-003** Every citation in the acceptance fixture opens the intended archived message in one selection. A stale citation yields the unavailable-source state.
- **SC-004** No-evidence, partial-coverage and verification-failure fixtures produce distinguishable outcomes.

## Assumptions

- The operator supplies a decision topic in the existing local explorer. This release covers one requested decision history at a time, with the existing project and authentication controls.
- History is reconstructed on demand over bounded Deep Recall evidence. Coverage may be partial. The standing decisions model remains available as a snapshot.
- A proposal, adoption, revision or supersession requires evidence for the specific action. A replacement needs an explicit relationship to the prior version. A reason is shown when evidenced and otherwise marked as undocumented for a supersession.
- The event date describes when the supporting message was recorded. Undated or ambiguous action evidence is visible outside the dated sequence. A missing adoption or resolution stays unknown.
- The feature depends on the existing Deep Recall configuration and the local explorer from #82 and #84. The existing boundary for model synthesis applies.
