# Feature Specification: Project mental models

**Feature Branch**: `029-project-mental-models`

**Created**: 2026-11-03

**Status**: Draft — planning review

**Input**: Issue #30: Build mental models for architecture, stack and decisions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand a project's standing picture (Priority: P1)

An agent joining a project reads its architecture, current stack and settled decisions
as three coherent summaries grounded in the imported history, without reconstructing
the picture from isolated search results.

**Why this priority**: This is the standing context missing from question-by-question recall.

**Independent Test**: Import two synthetic conversations that contribute complementary
architecture facts, prepare the project's models, and read them through the consumer
access surface. Verify both facts and their supporting conversation references.

**Acceptance Scenarios**:

1. **Given** complementary conversations for project alpha and competing facts for beta,
   **When** alpha's architecture model is read, **Then** it combines alpha's supported facts,
   identifies supporting conversations and contains no beta-only facts.
2. **Given** prepared models, **When** a consumer requests each of the three kinds,
   **Then** it receives architecture, current stack or decisions respectively, with project,
   kind and refresh information; decisions distinguish settled choices from proposals.
3. **Given** no completed model for a project, **When** it is read, **Then** the consumer
   receives an explicit missing result rather than a fabricated summary or silent recall fallback.

### User Story 2 - Refresh after importing history (Priority: P1)

An operator refreshes a project's standing picture after new history is successfully
imported, including a later conversation that supersedes an earlier stack decision.

**Why this priority**: A static summary misleads agents as the corpus changes.

**Independent Test**: Read an initial model, import a dated replacement decision, perform
the documented refresh and read again. Verify the replacement and retained rationale.

**Acceptance Scenarios**:

1. **Given** initial models and newly imported evidence, **When** the operator refreshes
   the project and completion is confirmed, **Then** subsequent reads reflect the new evidence.
2. **Given** existing models, **When** setup or refresh is repeated, **Then** there remains
   one logical model per project and kind.
3. **Given** refresh failure or timeout, **When** results are reported, **Then** no success
   is claimed; any previous content retains its actual successful refresh information.

### User Story 3 - Assess evidence and uncertainty (Priority: P2)

A consumer can distinguish supported conclusions from missing, contradictory or outdated
history and open the sanitized conversations supporting a summary.

**Why this priority**: Synthesis must remain inspectable rather than becoming a new authority.

**Independent Test**: Prepare sparse and conflicting synthetic evidence and verify explicit
uncertainty plus references resolvable through the existing conversation reader.

**Acceptance Scenarios**:

1. **Given** insufficient evidence for a kind, **When** its summary is read, **Then** it
   states the gap instead of inventing technologies or decisions.
2. **Given** incompatible accounts without an explicit resolution, **When** models are
   refreshed, **Then** the conflict remains visible rather than arbitrarily declared settled.
3. **Given** supporting references, **When** the consumer opens them, **Then** only sanitized
   archived conversation content is served.

### Edge Cases

- Unknown project, unclassified history, blank project and unsupported kind: explicit safe
  missing or invalid-input outcomes; never broaden to all projects.
- New import fails, is skipped unchanged, or is a dry run: no claim that models were refreshed.
- Refresh partially succeeds: report per-kind outcomes; do not claim an atomic three-model update.
- Concurrent refresh or ambiguous submission outcome: bounded failure/reconciliation, no
  unbounded polling or duplicate logical models.
- Deleted or unverifiable support: fail safely or omit unverifiable content with an explicit
  status; never substitute another project's evidence.
- Instructions embedded in history are evidence, not commands for the consumer or operator.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Maintain exactly three managed model kinds per explicitly selected project:
  architecture, current stack and architecture decisions.
- **FR-002**: Scope synthesis inputs and returned models to that project's existing project
  tag; unrelated and untagged evidence MUST NOT enter the model.
- **FR-003**: Derive model content exclusively from successfully imported, sanitized history;
  models MUST NOT replace the raw archive or be retained as original conversations.
- **FR-004**: Provide read-only consumer access to a selected project and model kind through
  the existing memory access surface, without consumer configuration against the memory engine.
- **FR-005**: Return project, kind, content, last successful refresh time and verifiable
  supporting conversation references with completed models. Never invent provenance for a synthesis.
- **FR-006**: Provide an explicit, repeatable operator workflow to create missing models and
  refresh existing models after imports, with bounded waiting and per-kind outcomes.
- **FR-007**: Repeating the workflow MUST preserve stable model identity and avoid duplicates.
- **FR-008**: A successful refresh MUST incorporate newly imported relevant history, distinguish
  explicit supersession from unresolved conflict and make insufficient evidence visible.
- **FR-009**: Missing, unavailable, invalid, pending and failed results MUST be distinguishable
  from a successfully completed model. Failed refresh MUST NOT advance successful-refresh metadata.
- **FR-010**: Consumer reads MUST NOT initiate creation or refresh. Operator maintenance MUST
  neither alter import success records nor trigger re-extraction of unchanged conversations.
- **FR-011**: Document import → refresh → consumer read, retry/recovery, scoping, freshness
  limits and how to open sanitized supporting conversations.
- **FR-012**: Verify model lifecycle, project isolation, evidence mapping and refresh behavior
  against the supported running memory engine using synthetic history before claiming acceptance.
- **FR-013**: Preserve safe errors and private logging: no original history, credentials,
  backend response bodies or personal corpus content in public output or committed evidence.

### Key Entities

- **Project model definition**: stable project/kind identity and standing synthesis question.
- **Project model snapshot**: completed derived summary, successful refresh time and supports.
- **Model support**: reference to imported conversation identity and its original provenance.
- **Refresh outcome**: selected project, kind, completion/failure state and safe error category.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a synthetic two-project corpus, all three model kinds are readable for alpha;
  its architecture answer includes two complementary expected facts from separate conversations
  and zero beta-only facts. Expected facts stay outside synthesis questions.
- **SC-002**: After a new dated decision is imported and refresh completes, the next read
  identifies the replacement choice and its supporting conversation for all affected kinds.
- **SC-003**: Every returned support resolves to the selected project's sanitized archived
  conversation; repeated setup/refresh leaves three logical models for that project.
- **SC-004**: Missing, sparse, conflicting and failed-refresh scenarios produce explicit
  outcomes, and a failed refresh never appears as a successful new snapshot.
- **SC-005**: An operator can follow the documented sequence from import through refresh to
  consumer read using only supported commands, without manual engine calls.

## Assumptions

- This is Phase 3 work authorized by §22, not an expansion of the MVP in §21. Dependency #25's
  read-only access surface is present; #31's general reflection/evaluation work remains separate.
- Refresh is explicit after a completed import, not automatic on every retained conversation.
  Operators are responsible for refreshing affected projects; refresh time is not proof that
  every later import is included. No scheduler or background worker is introduced.
- The existing shared bank and project-tag convention remain. Tags scope data, not authorization.
- Only the three fixed definitions are managed; arbitrary authoring/deletion, automatic discovery
  of all projects, general reflection, custom retrieval infrastructure and new sources are excluded.
- Model maintenance is importer-side derived-data maintenance over existing imports; consumers
  stay read-only. A decision record will document the new memory boundary contract.
- No automatic content-quality guarantee is inferred from a successful backend operation;
  live acceptance uses held-out expected topics, isolation checks and inspectable supports.

## Clarification Review

Scope, identity, lifecycle, errors, privacy and acceptance were reviewed on 2026-11-03.
Reasonable defaults are recorded above; no unresolved product clarification remains.
