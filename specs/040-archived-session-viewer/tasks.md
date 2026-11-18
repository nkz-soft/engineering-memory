# Tasks: Archived Session Viewer

Input: spec.md, plan.md, research.md, data-model.md and contracts/session-viewer.md.
Human continuation: `/issue-to-pr 86` after publication of Phase 1.

## Phase 1 — Setup

- [x] T001 Verify baseline and browser environment using tests/integration/test_explorer_browser.py.

## Phase 2 — Foundation

- [x] T002 Validate unchanged conversation boundary using tests/unit/test_access.py and tests/contracts/test_explorer_http.py.

## Phase 3 — US1 (P1): Recorded investigation

Independent test: synthetic source envelopes display readable requests/results/diffs, missing states and inert fallback.

- [x] T003 [US1] Add failing source/diff/missing-state scenarios in tests/integration/test_explorer_browser.py.
- [x] T004 [US1] Implement conservative recorded-field presentation in src/engineering_memory/api/explorer_assets/explorer.js.

## Phase 4 — US2 (P1): Exact evidence

Independent test: targets at 0/49/50/100 resolve on unlock, refresh and history navigation; malformed/stale targets fail.

- [x] T005 [US2] Add failing target and citation regression cases in tests/integration/test_explorer_browser.py.
- [x] T006 [US2] Implement fragment selectors, links, validation and focused navigation in src/engineering_memory/api/explorer_assets/explorer.js. Indexes must be nonnegative safe integers; tool fields require tool_index; text excludes it.

## Phase 5 — US3 (P2): Long output

Independent test: 10,000-line output starts collapsed, expands completely by keyboard and opens targeted fields.

- [x] T007 [US3] Add failing disclosure tests in tests/integration/test_explorer_browser.py.
- [x] T008 [US3] Implement 20-line/2,000-character previews and accessible full expansion in src/engineering_memory/api/explorer_assets/explorer.js and explorer.css.

## Phase 6 — Polish

- [x] T009 Document links, snapshot semantics and safe recorded evidence in docs/operations/local-memory-explorer.md.
- [x] T010 Run quickstart.md checks, review and fix findings; record outcomes in specs/040-archived-session-viewer/verification.md.

## Dependencies and delivery

T001 → T002 → US1 → US2 → US3 → polish. Test before implementation per slice. MVP is US1, but all stories are required for this issue. Shared browser file means sequential implementation. Independent HTTP and unit regression commands can run in parallel; documentation can be reviewed alongside final checks. No new services/schema/dependencies or extension hooks.
