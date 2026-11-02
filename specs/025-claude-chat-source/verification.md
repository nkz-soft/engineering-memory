# Verification: Claude chat source

## Test-first evidence

- Initial parser/contract invocation failed collection because ingestion.claude_chat did not exist.
  After implementing it: 23 passed.
- CLI selection tests before registration: 7 failed (missing --source). Replay tests failed
  collection because ClaudeChatArchiveSource did not exist. After registration/replay: 9 passed.
- Streaming test exposed coupling to private export state; policy moved into the source-local
  export adapter. Combined source/contract/CLI/replay checks: 34 passed.
- Review reproduced timestamp overflow and missing duplicate-error identity with two failing tests.
  Fixed by translating OverflowError and preserving validated native identity on format errors.
- Full suite initially: 2001 passed, 36 skipped, 1 failed (new module absent from constitutional
  layout). Recorded claude_chat in constitution 1.3.1 and updated the pinned module expectation.

## Code review

Independent reviewer inspected source, replay, CLI registration, tests and planning scope.
Two P2 findings above fixed and retested. Follow-up review reports no remaining blockers;
reviewer ran parser/CLI/module tests: 35 passed.

## Final checks

- `uv run ruff check .`: All checks passed.
- `uv run ruff format --check .`: 463 files already formatted.
- `git diff --check`: passed.
- `uv run pytest tests/integration/test_claude_live.py -q`: 1 skipped; isolated live contract
  stack was not opted in/configured. No live extraction or actual-engine Claude recall claimed.

The final full-suite result is recorded below. Supported export compatibility is
bounded by synthetic fixtures; no private vendor export was inspected or committed.

- Final `uv run pytest -q`: **2004 passed, 36 skipped in 88.85s** (exit 0).

PR: https://github.com/nkz-soft/engineering-memory/pull/67. Issue moved to in-review.
