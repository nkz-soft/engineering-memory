# Feature Specification: Hermes memory access

**Feature Branch**: `024-hermes-memory-access`
**Created**: 2026-11-02
**Status**: Draft — planning gate
**Input**: Issue #25, Configure Hermes against the shared bank and find an imported fact.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recall imported history from Hermes (Priority: P1)

An operator connects Hermes to the shared engineering history and asks about a fact
present only in imported ChatGPT history. Hermes retrieves it and identifies its source.

**Why this priority**: This is the Phase 1 consumer acceptance condition.
**Independent Test**: In a fresh Hermes conversation, ask about a synthesized imported
fact without supplying its answer; verify the answer and source identity.

**Acceptance Scenarios**:
1. **Given** an imported conversation, **When** Hermes searches for its distinctive
   fact, **Then** the result includes the fact, stable document identity and provenance.
2. **Given** an unrelated project with a competing fact, **When** search is scoped
   to the intended project and source, **Then** the competing fact is excluded.
3. **Given** no matching history, **When** Hermes searches, **Then** it receives an
   empty result rather than a fabricated answer or a backend failure.

### User Story 2 - Follow a fact to its conversation (Priority: P2)

A user follows the source identity to read sanitized messages in bounded pages.

**Why this priority**: Extracted facts alone cannot show the surrounding discussion.
**Independent Test**: Retrieve two consecutive pages for a known archived document.

**Acceptance Scenarios**:
1. **Given** an archived document, **When** its identity is requested, **Then** only
   sanitized normalized messages and source metadata are returned in original order.
2. **Given** an unknown identity, **When** requested, **Then** a clear not-found outcome
   is returned without exposing a filesystem path or original export bytes.

### User Story 3 - Reproduce the connection (Priority: P2)

An operator follows committed instructions to connect a fresh Hermes session.

**Why this priority**: A demonstration tied to an undocumented local setup cannot be repeated.
**Independent Test**: Follow the guide with explicit paths from a different working directory.

**Acceptance Scenarios**:
1. **Given** a working import environment, **When** the guide is followed, **Then**
   Hermes discovers the two retrieval tools and can repeat the fact lookup.
2. **Given** an unavailable backend, **When** search is attempted, **Then** failure
   is distinguishable from no matches and contains no credentials or private content.

### Edge Cases

- Empty query, invalid tags, invalid document identity and page bounds are rejected.
- End-of-conversation pages have no continuation; an offset beyond the end is empty.
- Missing, corrupt or unavailable archive records produce distinct safe failures.
- Backend failure is not converted to an empty successful result.
- Logs and startup output cannot corrupt the consumer connection or reveal secrets.
- Imported text is untrusted evidence, never instructions to execute.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hermes MUST retrieve through the project's read-only access surface,
  in accordance with ADR-008; no native consumer memory provider is configured.
- **FR-002**: Search MUST support an unscoped lookup and conjunctive project/source
  tag filtering, including `project:unknown`, with bounded result counts.
- **FR-003**: Every result MUST include content, stable document identity and the
  retained provenance: source, source id, original timestamp, project, repository
  when known and importer version.
- **FR-004**: Conversation retrieval MUST return only the sanitized normalized
  archive representation, paged by message with a continuation indicator.
- **FR-005**: The access surface MUST expose no write tool and open no network port.
- **FR-006**: Invalid input, no matches, not found and unavailable/corrupt dependencies
  MUST have distinct, credential-safe outcomes.
- **FR-007**: Committed documentation MUST describe prerequisites, local process
  configuration, explicit data paths, filtering, troubleshooting and verification.
- **FR-008**: Acceptance MUST include a fresh Hermes conversation retrieving a
  previously imported fact with provenance, without putting the answer in the prompt.
- **FR-009**: Public verification evidence MUST use synthesized conversations and
  omit real history, tokens, credentials and private machine configuration.

### Key Entities

- **Memory match**: Extracted fact, provenance and stable link to its source conversation.
- **Conversation page**: Identity, sanitized ordered messages and continuation offset.
- **Connection recipe**: Local executable, arguments and environment requirements.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One fresh Hermes conversation correctly answers a question from an
  imported synthetic fact and returns the matching source identity.
- **SC-002**: A scoped demonstration excludes all competing facts from a second project.
- **SC-003**: Paging reconstructs 100% of a synthetic multi-page conversation in order,
  without omitted or repeated messages; no secret sentinel appears in any result.
- **SC-004**: A second setup following only committed instructions discovers both
  retrieval capabilities and repeats the source-linked lookup.

## Assumptions

- ADR-008 supersedes the issue's older native-provider wording; this feature includes
  the initial access surface because `access` currently contains only a placeholder.
- #23 is closed and supplies the import/recall foundation; existing pipeline,
  shared `engineering-global` bank and archive remain authoritative.
- Tag matching follows the existing conjunctive boundary contract. Engine-specific
  matching modes and temporal search extensions are outside this feature.
- Reflect, conversation listing, other consumers, new sources, automatic recall,
  consumer writes and network deployment are outside scope.
- Live Hermes acceptance requires an operator's Hermes installation and model access;
  unavailable prerequisites must be reported, never replaced by a claimed live pass.

## Clarification Review

Scope, data identity, privacy, failures and acceptance are resolved by ADR-008 and
existing boundary contracts. No unanswered clarification questions remain. The
architecture interpretation above is an explicit assumption for planning review.
