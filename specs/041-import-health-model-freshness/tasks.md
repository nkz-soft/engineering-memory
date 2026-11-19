# Tasks — Import Health and Project-Model Freshness

## Foundation

- [x] T001 Test additive schema migration and atomic aggregates in `tests/integration/test_import_health.py`.
- [x] T002 Implement the bounded import health aggregate and migrate SQLite v1/v2 in `src/engineering_memory/ingestion/health.py` and `src/engineering_memory/ingestion/sqlite_state.py`.

## User Story 1 — Diagnose a missing import (P1)

- [x] T003 [US1] Test restart, source failure, unchanged retry, dry run and deferrals in `tests/integration/test_import_health.py`.
- [x] T004 [US1] Wire confirmed imports and completed attempts through `src/engineering_memory/ingestion/pipeline.py` and `src/engineering_memory/cli/runtime.py`, preserving the previous success time on failure.

## User Story 2 — Check freshness for a project (P2)

- [x] T005 [US2] Test metadata-only model reads and stale/current/unknown scope rules in `tests/unit/test_project_models_store.py` and `tests/unit/test_status.py`.
- [x] T006 [US2] Implement the metadata projection in `src/engineering_memory/memory/interface/project_models.py` and `src/engineering_memory/memory/hindsight/project_models.py`, and status reporting in `src/engineering_memory/access/status.py`.

## Explorer integration and verification

- [x] T007 Test the authenticated status contract and browser lifecycle in `tests/contracts/test_explorer_http.py` and `tests/integration/test_explorer_browser.py`.
- [x] T008 Expose and render operational status in `src/engineering_memory/api/explorer.py`, `src/engineering_memory/cli/explorer.py` and `src/engineering_memory/api/explorer_assets/`.
- [x] T009 Document the operator flow in `docs/operations/local-memory-explorer.md` and run the verification in `specs/041-import-health-model-freshness/quickstart.md`.

T001–T002 establish persistence before T003–T004. T005–T006 build the scoped read service on that contract. T007–T009 exercise the composed surface. Each test task must go red before its implementation task.
