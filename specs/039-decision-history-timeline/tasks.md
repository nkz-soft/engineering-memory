# Tasks — Source-Backed Decision History

## Setup

- [x] T001 Verify the approved worktree and load the contracts in specs/039-decision-history-timeline/contracts/decision-history.md.
- [x] T002 [P] Write and run failing decision history service and synthesis tests in tests/unit/test_decision_history.py.
- [x] T003 [P] Write and run a failing decision mode transport test in tests/contracts/test_explorer_http.py.
- [x] T004 [P] Write and run a failing browser journey in tests/integration/test_explorer_browser.py.

## User Story 1 — Follow a decision across sessions

- [x] T005 [US1] Add verified lifecycle events and bounded decision synthesis in src/engineering_memory/access/decision_history.py, deep_recall.py and synthesis.py in the same directory.
- [x] T006 [US1] Wire the mode into src/engineering_memory/access/service.py and src/engineering_memory/api/explorer.py.
- [x] T007 [US1] Render the lifecycle in src/engineering_memory/api/explorer_assets/index.html and explorer.js in the same directory.
- [x] T008 [US1] Verify both versions, reasons and action timestamps with tests/unit/test_decision_history.py.

## User Story 2 — Inspect chronology and disagreement

- [x] T009 [US2] Validate uncertain dates, ties and distinct unresolved accounts in src/engineering_memory/access/decision_history.py and render them in src/engineering_memory/api/explorer_assets/explorer.js.
- [x] T010 [US2] Verify visible uncertainty with tests/integration/test_explorer_browser.py.

## User Story 3 — Open the evidence

- [x] T011 [US3] Open exact sanitized messages through the existing citation viewer in src/engineering_memory/api/explorer_assets/explorer.js.
- [x] T012 [US3] Verify exact and stale sources and scope cancellation in tests/integration/test_explorer_browser.py.

## Verification

- [x] T013 Run the regression and browser checks in specs/039-decision-history-timeline/quickstart.md and the full suite.

## Dependencies

The three red test files can be written independently after setup. T005 supplies the response consumed by T006, which supplies the browser data for T007. The chronology and navigation checks use the shared detail from Story 1. Story 1 is the first usable slice. Story 2 can be exercised with conflicting evidence alone, and Story 3 with a single cited event.
