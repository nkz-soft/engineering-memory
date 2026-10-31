# Verification: Operator CLI

Validated on 2026-10-31 with Python 3.13.15, dependencies from `uv sync --locked`.

## Test-first evidence

Before implementation, enumeration and new command tests failed for absent iter_records, --json and status (11 failed, 9 passed). Import fixture tests then failed for absent runtime composition (3 failed, 1 skipped). The read-only enforcement test failed because status used a write-capable SQLite connection; adding read-only connection mode made it pass. The synthetic extraction fixture regression failed on JSON conversation payloads before its bounded synthetic-marker parser was extended.

Tests exercise real source parsing, local archive and SQLite adapters; only memory is replaced in offline CLI scenarios. Additional review coverage verifies terminal source failure preserves completed outcomes, state-write failure after retention reports its secondary error, and cancellation releases readers/memory/state resources. All history is synthesized.

## Commands and outcomes

The worktree's `.venv/Scripts/python.exe -m pytest` and `.venv/Scripts/ruff.exe` were used directly after locked sync because sandboxed uv could not write its global interpreter cache. Test runs used elevated tool execution to permit pytest temporary directories and subprocess checks.

- `.venv/Scripts/ruff.exe check .`: all checks passed.
- `.venv/Scripts/ruff.exe format --check .`: all files formatted.
- `.venv/Scripts/python.exe -m pytest -q --tb=short`: **1863 passed, 28 skipped in 86.36s**. Skips are opt-in live/infrastructure cases; CLI and nine real-engine contracts were also run explicitly with no skips.
- With `ENGINEERING_MEMORY_LIVE_CONTRACT=1`, `.venv/Scripts/python.exe -m pytest tests/integration/test_operator_cli.py -q --tb=short --show-capture=no`: **7 passed in 3.09s**. Includes real provision/import/unchanged skip/forced archive replay/status and recall of the synthetic cobalt-relay fact.
- With the same opt-in, `.venv/Scripts/python.exe -m pytest tests/integration/test_live_hindsight_contract.py -q --tb=short --show-capture=no`: **9 passed in 11.78s**. Confirms the fixture extension preserves existing real-engine contracts.
- `git diff --check`: no whitespace errors.

Live infrastructure: `docker compose -p cli21-validation -f deploy/hindsight/compose.contract.yaml up -d --wait --wait-timeout 600`. This is the pinned self-hosted real engine with synthetic extraction, not private history or an external paid model. Scratch banks are deleted by tests; the disposable stack/volume is removed after validation.

Initial live attempts failed because the extraction fixture expected plain text while the adapter sends serialized conversation JSON; the rejection led to failed operations and Windows socket errors during subsequent polling/cleanup. After a regression test and fixture correction, the complete live suite passed. An attempted separate Docker test runner was rejected by automatic approval review because of a whole-worktree mount into an external image; it was never run, and host validation succeeded instead.

## Code review

A separate reviewer inspected the working implementation against the specification, plan and CLI contract. No Critical or Important defect was found. Suggested failure-path coverage was added and passed. The architecture guard permits only the precise adapter-construction imports in the operator composition root; pipeline/domain/access imports remain forbidden. The older provision-only CLI expectation was updated to exercise all specified command help paths.

## Limits

No new schema, dependencies, source integrations or dry-run flag. Status reflects latest durable records, not historical skips. Structured application errors use the documented envelope; framework parser/help/version output remains Typer's. Live extraction is deterministic synthetic validation and does not establish real-model quality on a private corpus.

## CI colored-help follow-up

GitHub Actions forces Rich terminal styling, which can insert ANSI escape codes
inside an option name. Reproduced the reported failure with `TERM=xterm-256color`
and `GITHUB_ACTIONS=true`: the raw `--json` substring assertion failed. The help
test now checks `Text.from_ansi(...).plain` and explicitly covers both forced-color
and plain terminal modes. Application behavior is unchanged.

With those CI terminal variables set:
`.venv/Scripts/python.exe -m pytest -q --tb=short --color=no` —
**1864 passed, 28 skipped in 89.08s**.
Ruff lint and format checks both pass.
