# Tasks — ChatGPT export acquisition

Input: approved spec, plan, research, data model and contract. The second invocation of /issue-to-pr 40 approved implementation.

## Setup

- [x] T001 Resolve Spec Kit artifacts and verify the existing worktree and requirements checklist.

## User Story 1 — Refresh from a watched folder

- [x] T002 [US1] Write and observe failing discovery and staged ZIP preflight tests in tests/unit/test_export_acquisition.py.
- [x] T003 [US1] Implement discovery, ZIP preflight and durable publication in ingestion/acquisition modules, ingestion/chatgpt_preflight.py and archive/export_blobs.py.
- [x] T004 [US1] Write and observe failing coordinator and watcher CLI integration tests in tests/integration/test_export_acquisition.py.
- [x] T005 [US1] Wire the coordinator, store-scoped lock and one-shot command into CLI runtime.

## User Story 2 — Reject incomplete inputs and recover

- [x] T006 [US2] Write and observe failing ledger migration, compatibility, and interruption tests.
- [x] T007 [US2] Add the transactional ledger and resume from the verified archive, reusing the incremental importer.

## User Story 3 — Use the manual fallback and inspect freshness

- [x] T008 [US3] Write and observe failing manual and status acceptance tests.
- [x] T009 [US3] Project production evidence and completion time in both status modes.

## Verification

- [x] T010 Document ADR-007, scheduler setup and recovery.
- [x] T011 Verify the full suite and lint, obtain independent review and prepare the PR.
