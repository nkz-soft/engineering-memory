# Quickstart validation (after implementation)

Use only synthetic fixtures. From the feature worktree:

```powershell
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/contracts/test_codex_source.py
uv run pytest
uv run engineering-memory --help
uv run engineering-memory import --help
```

Follow the existing CLI import syntax with `--source codex` and a staged synthetic JSONL file. Confirm the implemented help before selecting positional paths or configuration options. First dry-run; then import against an explicitly provisioned local test bank. No real history is required.

Expected: original bytes and sanitized normalized conversation archived; codex:{native-id} identity and source:codex provenance. Repeat unchanged input and observe no extraction; modify a tool output and observe an update to that identity. Delete staged source and replay the original archive to prove independence. Use a valid/invalid/valid fixture batch and expect two imported sessions and one safe failure.

Live acceptance requires configured local Hindsight and the existing access surface. Recall a unique synthetic fact with source:codex plus its known project; verify the result and absence from a different-source filter. The implementation must add the exact opt-in test command here. Missing live configuration means UNVERIFIED, not PASS.

Planning verification only: review links, FR/SC coverage and constitution gates; no implementation tests are claimed in Phase 1.

## Implementation verification

Phase 2 uses `uv run pytest tests/unit/test_codex_source.py tests/contracts/test_codex_source.py tests/integration/test_codex_cli.py tests/integration/test_codex_live.py -q`.
The focused run passed 30 tests; the opt-in live test skipped. Tests first failed on missing
CodexSessionSource; CLI tests then failed on unsupported source selection before registration.
Review regressions for unknown events and directory symlinks both failed before their fixes.

`uv run ruff check .` passed; `uv run ruff format --check .` passed (501 files).
The first full suite found one obsolete expectation that Codex was unsupported; that parameter
was removed while Hermes/invalid refusal coverage remains. Final full-suite results are recorded
in the PR verification section.

Exact live command (isolated service required):

```powershell
$env:ENGINEERING_MEMORY_LIVE_CONTRACT = '1'
uv run pytest tests/integration/test_codex_live.py -q
```

Initial automated run skipped live acceptance because the isolated service was unavailable.
The operator subsequently started the isolated contract stack and supplied the successful output
on 2026-11-03:

```text
uv run pytest tests/integration/test_codex_live.py -v
tests/integration/test_codex_live.py::test_live_tool_root_cause_recall PASSED
1 passed in 4.16s
```

Live acceptance is VERIFIED by this operator-run result. The test covers actual-engine recall
with source/project filters, negative filters, unchanged skip and sanitized archive access.
Source-filtered recall through the in-memory contract store is also covered by
tests/integration/test_codex_cli.py.

Final full-suite verification: `uv run pytest -q` — **2084 passed, 38 skipped in 90.21s**.
`uv run engineering-memory import --help` also confirmed Codex selection and unchanged ChatGPT default.
