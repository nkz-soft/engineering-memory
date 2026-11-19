# Feature Specification: Evidence-backed session neighborhood

**Feature Branch**: `043-evidence-neighborhood`
**Created**: 2026-11-19
**Status**: Draft
**Input**: GitHub issue #89, step 8 of #81, depending on #84 and #86.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inspect the links around a session (Priority: P1)

A local explorer operator opens an archived session, selects its neighborhood, and inspects what connects the session to files, commits, pull requests and explicitly named continuation sessions.

**Why this priority**: The graph gives the operator a way to discover related work and check the basis for each connection.

**Independent Test**: Open a synthetic archived session with all four kinds of evidence and select one edge of each kind.

**Acceptance Scenarios**:

1. **Given** a session with a recorded successful edit, commit, PR reference and explicit continuation to an archived session, **when** the operator opens its graph, **then** the four relations are distinguishable and each selected edge shows its type and supporting record.
2. **Given** a selected edge, **when** the operator follows its evidence link, **then** the archived-session viewer reveals the supporting message or tool field.

### User Story 2 - Find sessions from a file (Priority: P2)

An operator enters a project-relative file path or selects a file in the graph and sees sessions with recorded edits to that file.

**Why this priority**: It lets operators find a session when they know the file but cannot name the session.

**Independent Test**: Import two projects with edits to the same relative path and use that path as the root in each project.

**Acceptance Scenarios**:

1. **Given** two projects containing `src/app.py`, **when** the operator opens that file in either project, **then** the graph shows only sessions editing the selected project's file.
2. **Given** an edit with ambiguous repository or file identity, **when** the operator browses either candidate, **then** the ambiguous record does not connect the candidates.

### User Story 3 - Explore a busy archive (Priority: P3)

An operator opens a heavily edited file and gets a usable neighborhood with clear coverage information.

**Why this priority**: High-degree nodes are common and should remain inspectable.

**Independent Test**: Open the same busy root twice against a synthetic large archive and compare the size, order and coverage indicators.

**Acceptance Scenarios**:

1. **Given** more neighbors than the display limit, **when** the operator opens the root, **then** the view shows a bounded, deterministic set and indicates truncation.
2. **Given** a visible session or file neighbor, **when** the operator selects it as the new root, **then** the explorer replaces the current neighborhood with that root's bounded view.

### Edge Cases

- The explorer distinguishes empty, unindexed, partial and unavailable evidence states.
- Failed edits, bare change claims, generic mentions of a prior session and unresolved continuation targets do not establish an edge.
- If a source record changes or goes missing, a stale anchor must not open a different record as evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** An authenticated local operator MUST be able to open a graph around the current archived session or an exact project-scoped file selection.
- **FR-002** Displayed edges MUST have one of four types: recorded file edit, recorded commit, PR reference or explicit continuation. PR references indicate a recorded reference.
- **FR-003** Selecting any displayed edge MUST show its type and a sanitized supporting record and offer a link to that precise viewer field.
- **FR-004** The system MUST keep equal relative paths in distinct projects or known repositories separate and omit associations with unresolved file scope.
- **FR-005** Each neighborhood MUST cap its depth and edge count and order ties deterministically. The operator MUST be told when the visible results are limited.
- **FR-006** Existing normalized archives MUST be eligible for indexing. Missing, stale or unsupported evidence MUST be handled without blocking ordinary session browsing.
- **FR-007** Nodes, edge details and evidence links MUST obey the existing local explorer's authentication and project scope.

### Key Entities

- **Root** — An archived session or a scoped file chosen by the operator.
- **Node** — An archived session, scoped file, scoped commit or qualified PR.
- **Edge** — A directed, typed assertion between two nodes with a supporting record.
- **Supporting record** — A sanitized archived message or tool field that can be opened in the viewer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** All four edge types in the acceptance fixture open the exact supporting field in the viewer.
- **SC-002** There are zero cross-project or cross-repository file joins in the equal-path collision fixture.
- **SC-003** Against 50,000 indexed synthetic sessions with at least 2,000 edits to one file, a request displays at most 30 direct edges, signals truncation and returns the same selection and order on repeated reads of unchanged evidence.
- **SC-004** The browser renders the busy-root response within two seconds of selection on the documented local test workstation with a prepared index. Evidence inspection remains keyboard operable.

## Assumptions

- A neighborhood shows one hop and at most 30 edges. Operators can reroot on a visible session or file.
- Initial recognition uses sanitized normalized records and conservative, source-specific evidence rules. Explicit continuations can use direct, resolvable user-authored references. Historical source metadata absent from normalized records does not imply a continuation.
- An operator prepares or refreshes a rebuildable local index for existing and newly imported history. The explorer shows its coverage state.
- The file entry point uses the active project and a known repository when present. Ambiguous project or repository identity is preferable to leave unresolved.
- The workflow uses the existing local explorer and archived-session viewer. PR and commit nodes are relation targets in the initial feature.
