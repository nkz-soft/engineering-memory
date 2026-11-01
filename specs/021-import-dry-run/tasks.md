# Tasks: Import dry run

Input: spec.md, plan.md, research.md, data-model.md and contracts/cli.md.

## Setup and foundation

- [x] T001 Confirm planning gate and existing boundaries in specs/021-import-dry-run/plan.md.

## US1: Preview safely (P1)

Independent test: synthetic corpus with poison side-effect adapters, full metadata and no secrets.

- [x] T002 [US1] Write failing metadata/no-side-effect tests in tests/unit/test_dry_run.py.
- [x] T003 [US1] Implement preview reports and shared preparation in src/engineering_memory/ingestion/report.py and pipeline.py.

## US2: Preserve subsequent import (P1)

Independent test: preview then real run with repeated identities; compare state and archive snapshots.

- [x] T004 [US2] Write failing read-only/parity tests in tests/integration/test_dry_run_cli.py.
- [x] T005 [US2] Compose read-only state and ephemeral sequential decisions in src/engineering_memory/cli/runtime.py and ingestion/pipeline.py.

## US3: CLI and partial previews (P2)

Independent test: both sources/output modes, force, failures, empty input, interruption.

- [x] T006 [US3] Write failing CLI contract/failure tests in tests/integration/test_dry_run_cli.py.
- [x] T007 [US3] Add flag and preview presentation in src/engineering_memory/cli/__init__.py and results.py.

## Polish

- [x] T008 Document usage and limits in README.md and ARCHITECTURE.md.
- [x] T009 Run full pytest/Ruff and independent code review; record evidence in specs/021-import-dry-run/tasks.md.

Dependencies: T001 → T002 → T003; T004 before T005; T006 before T007; T008/T009 after all stories.
Parallel opportunities: US2 storage fixture tests and US3 output tests can be authored independently;
execution remains sequential for shared source files. MVP is US1; ship all three stories together.
No extension hooks are configured. Test-first is required for each implementation slice.



## Verification evidence

- Red: pipeline dry-run API tests failed 4 times before implementation; CLI tests failed 6 times
  on the absent flag. Review guard tests failed 2 times before the fix. Preview-log regression
  failed once before projected log statuses were added.
- Final: `uv run pytest -q --basetemp=.venv/final-suite` — 1883 passed, 28 skipped in 83.62s.
- `uv run ruff check .` — All checks passed.
- `uv run ruff format --check .` — 409 files already formatted.
- Independent read-only code review: missing real-run adapters must fail before any side effect;
  fixed test-first, then re-reviewed. No remaining actionable findings; final log change approved.
- Skipped tests retain existing opt-in/platform requirements; no live extraction used for preview.
- Source policy note: ChatGPT rejects duplicate native ids as recoverable source errors. Generic
  conforming sources use the ephemeral overlay; both behaviors are tested without changing policy.
