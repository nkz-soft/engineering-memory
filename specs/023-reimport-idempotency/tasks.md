# Tasks: Re-import idempotency

**Input**: spec.md, plan.md, research.md, data-model.md and contracts/reimport.md.

## Phase 1: Setup

- [x] T001 Verify committed plan, approved continuation, dependencies and ignore rules in specs/023-reimport-idempotency/plan.md and .gitignore.

## Phase 2: Foundation

- [x] T002 Write failing recall/submission/extraction evidence controls in tests/integration/test_import_recall_e2e.py.
- [x] T003 Implement controlled two-member corpus, forwarding observer and strict evidence assertions in tests/integration/test_import_recall_e2e.py; each member has a distinct stable id and one fact.

## Phase 3: US1 — Unchanged replay (P1, MVP)

Independent test: unchanged replay yields zero submissions/extraction and exactly both recalled identities.

- [x] T004 [US1] Write and run the failing unchanged replay case in tests/integration/test_import_recall_e2e.py before adding its harness.
- [x] T005 [US1] Implement real baseline/replay harness and unchanged verification in tests/integration/test_import_recall_e2e.py.

## Phase 4: US2 — State loss (P1)

Independent test: remove only disposed temporary state, replay through fresh adapters and observe both original ids without duplicates.

- [x] T006 [US2] Write and run failing recovery scenario in tests/integration/test_import_recall_e2e.py.
- [x] T007 [US2] Implement state deletion/recreation and fresh adapter recovery in tests/integration/test_import_recall_e2e.py.

## Phase 5: US3 — Changed conversation (P2)

Independent test: exactly one changed id submitted, replacement fact visible, unchanged fact preserved.

- [x] T008 [US3] Write and run failing edited-content scenario in tests/integration/test_import_recall_e2e.py.
- [x] T009 [US3] Implement changed-corpus replay and stale-fact checks in tests/integration/test_import_recall_e2e.py.

## Phase 6: Required gate and verification

- [x] T010 Write failing missing/skipped/error/failure controls for all three required scenarios in tests/unit/test_e2e_runner.py, then register them in deploy/hindsight/e2e.py.
- [x] T011 Run offline, lint, formatting, live contract and repeated E2E verification; record red/green evidence in specs/023-reimport-idempotency/quickstart.md.
- [x] T012 Review finished diff, fix findings and publish template-based PR referencing #24 and specs/023-reimport-idempotency/.

## Dependencies and execution

T001 -> T002 -> T003; each story's failing test precedes its harness change. US1 builds shared import infrastructure; US2 and US3 independently establish baselines. Execute shared-file changes sequentially. Runner controls in tests/unit/test_e2e_runner.py can be authored independently of corpus helpers; live cases must run serially because extraction statistics are global. Deliver all stories, then the required runner gate and review. No parallel agents are needed for implementation.
