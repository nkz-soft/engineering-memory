# Tasks: Automatic Coding-Agent Session Import

## Setup and foundations

- [x] T001 Cover configuration and source layouts in tests/integration/test_session_import.py.
- [x] T002 Add capture settings and discovery in src/engineering_memory/settings.py and src/engineering_memory/ingestion/session_capture.py.

## User Story 1 - Import on demand

Independent test: run one command against two synthetic histories and search both sources.

- [x] T003 [US1] Test capture, recall, identity, unchanged extraction and replay in tests/integration/test_session_import.py.
- [x] T004 [US1] Stage stable bytes, decode through the native adapters and compose the CLI in src/engineering_memory/ingestion/session_capture.py and src/engineering_memory/cli/runtime.py.

## User Story 2 - Schedule imports

Independent test: invoke the same one-shot action as a scheduled job and check overlap and recovery.

- [x] T005 [US2] Test contention and process exit in tests/unit/test_session_capture.py.
- [x] T006 [US2] Serialize capture invocations in src/engineering_memory/cli/session_lock.py and document opt-in scheduling in docs/operations/session-import.md.

## User Story 3 - Report and retry failures

Independent test: inspect the summary for a mixed run, fix the failed file and repeat.

- [x] T007 [US3] Test capture races, link exclusion and resumable failures in tests/unit/test_session_capture.py and tests/integration/test_session_import.py.
- [x] T008 [US3] Emit safe per-source results and meaningful exit codes in src/engineering_memory/cli/results.py and src/engineering_memory/cli/runtime.py.

## Verification

- [x] T009 Run focused and full checks and record live recall and scheduler acceptance in specs/037-automatic-session-import/quickstart.md and the pull request.
