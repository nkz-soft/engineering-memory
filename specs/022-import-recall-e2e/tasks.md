# Tasks: Import and recall end to end

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/e2e.md

## Phase 1: Setup
- [x] T001 Verify checklist, tools and ignored paths; record environment in specs/022-import-recall-e2e/verification.md

## Phase 2: Foundation
- [x] T002 Write failing completeness and lifecycle controls in tests/unit/test_e2e_runner.py
- [x] T003 Add testcontainers dev dependency in pyproject.toml and uv.lock; implement isolated lifecycle and report guard in deploy/hindsight/e2e.py

## Phase 3: User Story 1 — Retrieve an imported decision (P1)
**Independent test**: A clean live import recalls a known decision with complete provenance, tags, original time and persisted local evidence.
- [x] T004 [US1] Write live import/recall assertions and negative evidence controls in tests/integration/test_import_recall_e2e.py
- [x] T005 [US1] Run the live test and fix harness or actual defects, preserving production interfaces, in tests/integration/test_import_recall_e2e.py and deploy/hindsight/e2e.py

## Phase 4: User Story 2 — Detect regressions in review (P1)
**Independent test**: Missing/skipped cases, omitted fields, wire time loss and dependency failures cannot yield a successful gate.
- [x] T006 [US2] Demonstrate provenance/tag/time omission sensitivity in tests/integration/test_import_recall_e2e.py
- [x] T007 [US2] Write failing CI selection control in tests/structure/test_ci_workflow.py and add required live job in .github/workflows/ci.yml

## Phase 5: Verification and review
- [x] T008 Run lint, format, full offline suite, existing live contracts and two clean end-to-end runs; record evidence in specs/022-import-recall-e2e/verification.md
- [x] T009 Request independent code review and resolve findings; update specs/022-import-recall-e2e/quickstart.md
- [ ] T010 Commit, push and create template-compliant PR; record issue label transition in specs/022-import-recall-e2e/verification.md

## Dependencies and execution
T001 -> T002 -> T003 -> US1 (T004–T005) -> US2 (T006–T007) -> T008–T010.
Tests precede implementation. US1 is the MVP; US2 makes it a required review gate. No tasks are marked parallel because harness and live tests share setup. Independent review occurs after verification.



