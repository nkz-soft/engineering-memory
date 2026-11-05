# Tasks: Project mental models

Input: approved plan/specification, resumed by `/issue-to-pr 30` on 2026-11-04.
Tests precede implementation; each test batch must fail for the missing behavior first.

## Phase 1: Setup

- [x] T001 Inspect committed plan, constitution and live prerequisites; initialize `.venv`.
- [x] T002 Resolve pinned wire/lineage contracts in `specs/029-project-mental-models/research.md`.

## Phase 2: Foundation

- [x] T003 Write failing validation/result tests in `tests/unit/test_project_models.py`.
- [x] T004 Implement neutral key/snapshot/support/read/outcome types and separate protocols in `src/engineering_memory/memory/interface/project_models.py`; project is exact nonblank classified slug, kinds architecture/stack/decisions, aware refresh timestamps, nullable stale.

## Phase 3: US1 — Standing picture (P1)

Independent test: two supporting conversations produce one scoped model read with archive references.

- [x] T005 [US1] Write failing HTTP read/provenance/isolation tests in `tests/unit/test_project_models_store.py`.
- [x] T006 [US1] Implement bounded read, stable identity, definition/tag checks and source resolution in `src/engineering_memory/memory/hindsight/project_models.py`.
- [x] T007 [US1] Write failing service and MCP tests in `tests/unit/test_project_model_access.py` and `tests/integration/test_access_mcp.py`.
- [x] T008 [US1] Implement read-only tool and composition in `src/engineering_memory/access/service.py`, `server.py` and `cli/runtime.py`.

## Phase 4: US2 — Refresh (P1)

Independent test: refresh after new import updates the model; repeated refresh preserves three identities.

- [x] T009 [US2] Write failing lifecycle/timeout/reconciliation tests in `tests/unit/test_project_models_store.py`.
- [x] T010 [US2] Implement strict fixed definitions and bounded explicit refresh in `src/engineering_memory/memory/hindsight/project_models.py`.
- [x] T011 [US2] Write failing partial-outcome and CLI tests in `tests/unit/test_project_model_cli.py`.
- [x] T012 [US2] Implement importer maintenance and CLI composition in `src/engineering_memory/ingestion/project_models.py` and `src/engineering_memory/cli/`.

## Phase 5: US3 — Evidence and uncertainty (P2)

Independent test: valid lineage opens sanitized archive; invalidated/foreign/unresolved lineage fails closed.

- [x] T013 [US3] Test observation lineage, sparse/conflicting evidence, last-good failure and live import/refresh/read in `tests/integration/test_project_models_live.py`; extend required gate in `deploy/hindsight/`.
- [x] T014 [US3] Fix behavior exposed by T013, including bounded citation traversal and explicit missing/pending/stale outcomes in `src/engineering_memory/memory/hindsight/project_models.py`.

## Phase 6: Verification and review

- [x] T015 [P] Document operator/client sequence and ADR in `docs/operations/project-models.md`, `README.md`, `ARCHITECTURE.md` and feature contracts.
- [ ] T016 Run full tests, lint/format, live lifecycle and real-extractor acceptance; record actual evidence in `specs/029-project-mental-models/verification.md`.
- [x] T017 Request independent review, fix findings, push and open PR using `.github/pull_request_template.md`.

PR #72 remains draft: stricter source-quote validation exposed generation failures after the
initial keyword-only real-model runs passed. Manual review found unsupported attributed motives;
the chosen model must pass the stricter contract before semantic acceptance can be completed.

## Dependencies and strategy

Foundation → US1 → US2 → US3 → verification/review. US1 is the first useful read-only slice;
US2 makes it maintainable. Within each story tests precede code. Documentation T015 may proceed
independently once contracts stabilize. Example independent work: service tests and HTTP tests
use different files after T004; live scenario design and documentation can proceed after T012.
No implementation test result substitutes for a missing live acceptance run.
