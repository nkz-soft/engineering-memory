# Tasks: Evidence-backed session neighborhood

Input: [specification](spec.md), [plan](plan.md), [research](research.md), [data model](data-model.md), [contract](contracts/neighborhood.md), [quickstart](quickstart.md).

## Setup

- [x] T001 Verify the committed plan, feature worktree, and requirements checklist in specs/043-evidence-neighborhood/checklists/requirements.md.

## Foundation

- [x] T002 [P] Demonstrate red tests for guarded snapshots and source record verification in tests/unit/test_neighborhood_access.py.
- [x] T003 [P] Demonstrate red tests for transactional refresh and scoped indexed adjacency in tests/unit/test_neighborhood_index.py.
- [x] T004 Implement transactional SQLite publication and independent bounded lookups in src/engineering_memory/access/neighborhood_index.py.

## User Story 1 — Session evidence (P1)

- [x] T005 [P] [US1] Demonstrate red native record tests for four relation types and failed outcomes in tests/unit/test_neighborhood_evidence.py.
- [x] T006 [P] [US1] Demonstrate red authentication, evidence navigation and command tests in tests/contracts/test_explorer_http.py, tests/integration/test_explorer_browser.py and tests/unit/test_explorer_cli.py.
- [x] T007 [US1] Implement conservative archive projection and exact snapshot guards in src/engineering_memory/access/neighborhood_evidence.py.
- [x] T008 [US1] Implement shared scoped index and current archive reads in src/engineering_memory/access/service.py and src/engineering_memory/access/neighborhood.py.
- [x] T009 [US1] Expose authenticated graph, evidence and guarded viewer reads in src/engineering_memory/api/explorer.py and wire refresh and launch in src/engineering_memory/cli/runtime.py and src/engineering_memory/cli/__init__.py.
- [x] T010 [US1] Add session graph, typed edge selection and verified transitions in src/engineering_memory/api/explorer_assets/explorer.js.

Independent test: open a synthetic session and follow a relation of each type to its supporting field.

## User Story 2 — File entry and isolation (P2)

- [x] T011 [US2] Test identical paths across projects/repositories and ambiguous input in tests/unit/test_neighborhood_index.py and tests/contracts/test_explorer_http.py.
- [x] T012 [US2] Add exact repository-relative entry and reroot controls in src/engineering_memory/api/explorer_assets/index.html and src/engineering_memory/api/explorer_assets/explorer.js.

Independent test: query the same path for distinct project/repository pairs and inspect the resulting sessions.

## User Story 3 — Busy archives (P3)

- [x] T013 [US3] Validate deterministic indexed lookup, cap and truncation on the large synthetic fixture in tests/unit/test_neighborhood_index.py.
- [x] T014 [US3] Validate truncation, partial or absent index, stale evidence and lock/reroot races in tests/integration/test_explorer_browser.py.

Independent test: open a high-degree file twice and compare order, edge count and the visible truncation state.

## Verification

- [x] T015 Document refresh, typed evidence and coverage in docs/operations/local-memory-explorer.md and record acceptance results in specs/043-evidence-neighborhood/verification.md.
- [x] T016 Run focused and repository checks, obtain independent review and update specs/043-evidence-neighborhood/tasks.md.

## Dependencies and parallel work

Projection, index adapter and browser tests can progress against the agreed data and HTTP contracts while shared read and CLI composition are prepared. Exercise US1 end to end before accepting US2 and US3. Each behavior increment follows red, green and refactor.
