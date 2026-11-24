# Tasks: Retain reconciliation

- [x] T001 Reproduce slow, uncertain and terminal retain outcomes via synthetic CLI tests in `tests/integration/test_retain_reconciliation.py`.
- [x] T002 Add the tracked capability in `memory/interface` and interpret operation results in `memory/hindsight/store.py`.
- [x] T003 Persist receipts and atomically settle outcomes in `ingestion/sqlite_state.py`.
- [x] T004 Wire reconciliation through `ingestion/pipeline.py` and report it through manual import, automatic capture and offline status.
- [x] T005 Run the pinned isolated backend acceptance check and the regression suite. Document operator behavior.
