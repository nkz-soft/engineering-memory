# Verification: Claude Code session source

Date: 2026-11-02. Branch: `026-claude-code-source`.

## Test-first evidence

- Context/model tests: 2 failures before optional source context existed; passed after model and sanitizer changes.
- Source/parser tests: 16 failures from the missing reader, then 18 focused parser/context tests passed.
- Metadata classification: 8 failures from missing classifier; source contract + classifier run then passed 17 tests.
- CLI/replay/provenance: 5 failures from unsupported source/missing archive reader; composition then passed.
- Independent review found two P1 defects: selected-symlink iteration repeated forever, and escaped
  newlines in tool JSON bypassed multiline PEM scanning. Regression tests observed failure before
  correction; both are fixed. Multiline request/diff and result cases were also checked red/green by
  temporarily restoring the old whole-text scan and then restoring structured scanning.
- A valid Unicode paragraph separator was rejected by broad line splitting; a failing test preceded
  the LF-only record-splitting correction.
- The live extraction fixture initially rejected nested tool-result JSON; a failing fixture unit test
  preceded its bounded escaped-quote support. The live test was rerun successfully after correction.

## Final commands and outcomes

```text
uv run ruff check .
All checks passed!

uv run ruff format --check .
483 files already formatted

uv run pytest -q --tb=short
2052 passed, 37 skipped in 74.22s

git diff --check
exit 0
```

The default suite intentionally skips opt-in live/container scenarios. It is not counted as live
verification. With the repository's isolated contract stack ready, separately ran:

```powershell
$env:ENGINEERING_MEMORY_LIVE_CONTRACT='1'
uv run pytest tests/integration/test_claude_code_live.py tests/integration/test_claude_live.py tests/integration/test_live_hindsight_contract.py -q --tb=short
# 11 passed in 15.41s
```

This exercised real Hindsight retention/recall/filtering, Claude Code root-cause recall from tool
output, unchanged import skip, sanitized access, existing Claude-chat recall and established live
engine contracts. Only extraction was synthetic. The disposable `issue27-live` compose project,
containers, network and scratch volume were removed after success.

## Review

Independent read-only review rechecked both P1 corrections and reported no remaining actionable
P1/P2 issues, ready subject to the full-suite checks above. Unsupported vendor dialect variants,
live acquisition, external-output acquisition and subagent aggregation remain explicitly outside
this source's approved scope. Basename collisions and context-only refresh behavior are documented
in the import guide and ADR-010.

Published implementation: https://github.com/nkz-soft/engineering-memory/pull/68. Issue #27 moved to in-review. Worktree retained for review.

## PR secret-scan follow-up

CI flagged five assembled-in-source synthetic password assignments as generic API keys. These were
invented test values, not credentials. The tests now assemble those values at runtime, following
the repository's synthetic-fixture convention; runtime test inputs are unchanged. The two original
implementation/handoff commits were replaced on this feature branch so the literals do not remain
in reachable history. Planning commit db31b89 is unchanged.

After the fixture-only change, `uv run ruff check .` passed and the focused source/context/CLI
selection passed 37 tests. The pinned Gitleaks v8.30.1 scanner was run over an isolated single-branch
clone (a Linux container cannot directly follow the Windows worktree's .git pointer):
35 commits scanned, approximately 3.23 MB, no leaks found. The initial direct worktree-container
invocation scanned zero commits and was rejected as invalid evidence despite its zero exit code.
