# Tasks: Persistent Import State

## Setup

- [x] T001 Confirm approved artifacts, clean worktree, complete requirements checklist and absent hooks in specs/013-sqlite-import-state/.
- [x] T002 Add failing dependency declaration expectation in tests/structure/test_packaging.py; add SQLAlchemy >=2,<3 in pyproject.toml and lock with uv.

## Foundation

- [x] T003 Write failing concrete adapter contract fixtures in tests/contracts/test_sqlite_state_passes_the_contract.py covering all IS-1–IS-9 hooks.
- [x] T004 Write failing lifecycle, schema/version, timestamp, opaque-ID, rollback, persistence/subprocess, lock and safe-error tests in tests/unit/test_sqlite_state.py.
- [x] T005 Implement SQLAlchemy Core adapter and lifecycle in src/engineering_memory/ingestion/sqlite_state.py: composite primary key `(source, source_id)`, all fields NOT NULL except error; status imported/failed only; nonempty error for failed and NULL for imported; UTC timestamp text; version 1 singleton; safe boundary errors.

## US1 — Refresh without paying twice

- [x] T006 [US1] Write failing persistent refresh/change/title tests in tests/integration/test_persistent_import_state.py and prove repeated retain counts with the existing harness.
- [x] T007 [US1] Verify src/engineering_memory/ingestion/sqlite_state.py passes durable repeated import and canonical original-hash tests without new hashing policy.

## US2 — Resume failed work

- [x] T008 [US2] Write failing retry/continuation/unavailable-state tests in tests/integration/test_persistent_import_state.py, including lookup failure before retain and failure after retain.
- [x] T009 [US2] Verify failed records and replacement semantics through src/engineering_memory/ingestion/sqlite_state.py; no production importer added.

## US3 — Reapply processing

- [x] T010 [US3] Write failing force decision tests in tests/unit/test_import_state_rules.py and forced original-based replay in tests/integration/test_persistent_import_state.py.
- [x] T011 [US3] Add keyword-only force=False to may_skip in src/engineering_memory/ingestion/state.py and run in tests/integration/pipeline.py; force bypasses skip only.

## US4 — Preserve missing history

- [x] T012 [US4] Write missing/empty export preservation tests in tests/integration/test_persistent_import_state.py checking actual state/archive/bank and absence of retain calls.
- [x] T013 [US4] Verify import paths in tests/integration/pipeline.py never derive removals or reconcile export membership.

## Polish and verification

- [x] T014 Update ARCHITECTURE.md §§17/20, specs/007-boundary-interfaces/contracts/interfaces.md and adapter usage in specs/013-sqlite-import-state/quickstart.md.
- [x] T015 Run full pytest, Ruff lint/format, uv lock --check and git diff --check; record red/green evidence in specs/013-sqlite-import-state/verification.md.
- [ ] T016 Request independent review, resolve findings, commit/push, compose PR from .github/pull_request_template.md, attach PR and move issue #14 to in-review.

## Dependencies and independent checks

T001 → T002 → T003/T004 → T005 → story checks. US1 is the first viable increment. US2 reuses the adapter and existing failure handling; US3 adds shared force policy; US4 protects existing no-removal behavior. Test files can be authored separately but edits to the shared harness/policy remain sequential. All tests precede their corresponding implementation. The complete approved scope includes all four stories, not only the MVP increment.
