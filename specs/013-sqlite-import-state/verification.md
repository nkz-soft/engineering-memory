# Verification: Persistent Import State

## Scope and execution

Approved Phase 2 resumed through `/issue-to-pr 14`. The requirements checklist had 16 completed items and zero unchecked items. There are no extension hooks. Spec Kit resolved the committed feature directory and tasks. This feature adds a production state adapter; production importer/CLI wiring remains #19.

## Test-first evidence

- Updated the dependency expectation before adding SQLAlchemy: packaging check failed because sqlalchemy was absent, then passed after `uv add "sqlalchemy>=2,<3"`.
- Wrote adapter contract and database tests before the adapter. Initial collection reported the missing adapter and SQLAlchemy; after dependency installation the concrete adapter fulfilled the existing contract. The first executed database run passed 28 checks with one invalid test fixture (whitespace in an opaque identifier); corrected the fixture to the existing model's no-whitespace contract.
- `uv run pytest tests/unit/test_import_state_rules.py -q --tb=short`: 2 failed / 4 passed before force implementation, rejecting the missing force keyword; force-aware decision now passes.
- `uv run pytest tests/integration/test_persistent_import_state.py -q --tb=short`: 4 failed / 5 passed before harness force support; failures identified the missing force keyword. Acceptance scenarios now pass.
- Reader-open race regression failed because the old connector recreated a missing empty database and returned corruption. SQLite URI mode=rw now refuses creation and returns unavailable.
- Foreign-view-only schema regression failed because initialization adopted the database. Initialization now rejects it without repair.
- Review regressions for ordinary/expression unique indexes and case-altered CHECK values failed before validation fixes. Validation now checks the complete SQLite index catalog and preserves literal values during CHECK comparison.

## Review

Independent read-only code review was requested through the repository's requesting-code-review skill. The reviewer identified incompatible unique indexes/constraints and CHECK comparison changing string literals. The expression-index variant exposed SQLAlchemy reflection's omission and was reproduced separately. All were fixed and the reviewer confirmed every finding closed. Added a real reader during an uncommitted write and initialization-commit rollback coverage.

## Acceptance evidence

Tests exercise all shared IS-1–IS-9 rules, real locked/corrupt files, subprocess persistence, opaque IDs and timezone precision, atomic rollback, initialized/versioned schemas, independent readers, fixed safe diagnostics and no accidental database recreation. Integration counts memory calls and uses real local archive/source/sanitizer/state to prove unchanged skips, one-character changes, failure retry/continuation, forced replay under changed sanitization, missing/empty export preservation and retain-success/state-failure resending.

`uv run pytest tests/unit/test_sqlite_state.py -q --tb=short`: 23 passed after final schema fixes.

## Full-suite timing observation

An intermediate full run passed 1,563 tests with four skips. After review coverage was added, a run passed 1,570 tests with four skips. A subsequent loaded-host run failed the unchanged `tests/unit/test_alias_matcher.py::test_a_realistic_rule_set_scans_a_realistic_conversation_quickly` timing check (5.74s versus 1.5s), with 1,570 other tests passing. Its isolated rerun passed in 0.91s total; the classifier and its test were not changed. Final complete rerun results follow below.

## Limitations

Four existing skips cover two unsupported failure hooks on a fake memory adapter and two Windows symbolic-link permission cases. There is no live Hindsight instance claim. Local state and memory retention are separate commits; a partial failure can repeat extraction under the stable document ID. Single local writer is the supported model.

## Final verification

- `uv run pytest tests/unit/test_alias_matcher.py::test_a_realistic_rule_set_scans_a_realistic_conversation_quickly -q --tb=short`: 1 passed in 0.91s.
- `uv run pytest -q --tb=short -rs`: **1571 passed, 4 skipped in 49.19s**.
- `uv run ruff check .`: **All checks passed!**
- `uv run ruff format --check .`: **289 files already formatted**.
- `uv lock --check`: **Resolved 27 packages**, exit 0.
- `git diff --check`: exit 0; staged check repeated before commit.

All code-review findings are resolved. No implementation deviations from the approved scope. Schema rejection is intentionally conservative for this owned versioned layout; database-specific validation remains inside its adapter.

## Delivery

Implementation commit: 791bed4. PR: https://github.com/nkz-soft/engineering-memory/pull/53. Issue #14 moved from in-progress to in-review. All 16 tasks completed; the isolated worktree remains for review. No merge was performed.
