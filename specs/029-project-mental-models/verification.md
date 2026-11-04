# Verification: Project mental models

Date: 2026-11-04. Feature: issue #30, branch `029-project-mental-models`.
Base implementation checkout: `90261a5`; planning commits `8e4fbed`, `ec7a149`.

## Current result

Implementation, offline regression checks, isolated live protocol/lifecycle gate and existing
engine contract gate pass. **Real-model semantic acceptance remains pending** an external LLM
configuration. The PR remains draft until that acceptance is recorded. Fixture-generated text
is not evidence of actual model synthesis quality. T016 remains open for that reason.

## Environment

- Windows host, Python 3.13.15, uv 0.12.5, Docker server 29.9.2.
- Hindsight 1.1.0, pinned image digest
  `sha256:50311d02b4d5d2b7c5242bd336edf8735df8374eaad496a92f49c83b37d2aa06`.
- Locked existing application/test dependencies; no runtime dependency change.
- All test corpora are synthetic. Disposable banks, archives, import state and backend containers
  are separate from operator data. Test runners remove only their own labelled resources.

## Test-first evidence

Observed red before implementing each slice:

- `tests/unit/test_project_models.py`: 2 failures for missing neutral contracts → 2 passed.
- `tests/unit/test_project_models_store.py`: 15 missing-adapter failures → read/isolation/lineage
  cases passed; 6 missing-refresh failures → lifecycle/timeout/reconciliation cases passed.
- `tests/unit/test_project_model_access.py`: missing models constructor argument → archive-backed
  read/validation tests passed, with existing service and actual stdio regressions.
- `tests/unit/test_project_model_cli.py`: 5 missing-command failures → 5 passed.
- Fixture tool completion and deliberate synthesis-failure tests failed before fixture support.
- Required-model gate test failed because missing model cases were accepted, then passed after
  extending the required set. Architecture composition-allowance test also failed first.
- Independent review reproduced two production defects. Regression tests observed failed first
  generation as pending and unbounded lock wait; both failed before fixes, then passed.
- Final adapter unit run: 23 passed, including both review regressions.

An initial full run found the architecture guard's missing new constructor allowance; fixed
with an explicit regression preserving consumer/ingestion import rejection. An initial live
failure-injection attempt used unsupported bank-level LLM config; replaced with deliberate
fixture LLM failure and zero test-worker retries, then verified last-good preservation live.

## Commands actually run

Commands below use the worktree's locked environment. The `.venv/Scripts/python` spelling
avoids unrelated global environments; it is equivalent to `uv run python` after `uv sync --frozen`.

| Command | Result |
|---|---|
| `uv sync --frozen` | Environment created from existing lock; package installed |
| `.venv/Scripts/python -m pytest -q --tb=short` | 2134 passed, 42 skipped; 89.78 seconds |
| `.venv/Scripts/python -m ruff check .` | All checks passed |
| `.venv/Scripts/python -m ruff format --check .` | 531 files already formatted at final check |
| `git diff --check` | Passed |
| `.venv/Scripts/python deploy/hindsight/e2e.py` | Final expanded gate: 36 passed, no skips; 45.82 seconds for pytest |
| `.venv/Scripts/python deploy/hindsight/contract.py` | 9 passed, no skips; 13.18 seconds for pytest |
| `.venv/Scripts/engineering-memory --help` | New models command listed, exit 0 |
| `.venv/Scripts/engineering-memory models refresh --help` | Project/kind/JSON options listed, exit 0 |

Normal-suite skips are opt-in live cases; the required live suites above executed without skips.
Later test-harness changes only add optional synthetic evidence capture and its documentation;
the final real-model run must record its actual command/result separately.
Redacted staged secret scan, `gitleaks git --staged --redact --no-banner`, scanned approximately
85 KB and reported no leaks before the implementation commit.

## Live backend coverage

The required e2e runner now rejects absent, duplicate, skipped, failed or spoofed model cases.
It ran the existing import/recall, unchanged/state-loss/changed replay and coding-agent stdio
journeys, plus three model cases:

1. Import two complementary conversations; create/read all three kinds, reject beta and
   untagged lexical competitors, open sanitized supports, repeat refresh without duplicates,
   import superseding relay/database decisions and refresh/read all affected kinds.
2. Preserve last-good content and successful time after a backend generation failure;
   expose failure time. The LLM fixture fails deliberately; backend operations/state are real.
3. Keep unresolved competing Rust/Go proposals visible, with supports and no invented
   unrelated technology choice. This fixture run validates protocol, not semantic quality.

HTTP adapter tests also cover observation source-ID expansion, invalidated/foreign/missing
lineage, incompatible definitions, bounded traversal, timeout, ambiguous POST and lock deadline.
The isolated engine run establishes actual fact-detail provenance resolution; observation
expansion additionally has pinned-source research and HTTP contract tests, not a claim that
this run produced consolidated observations.

## Independent review

Read-only reviewer found and rechecked fixes for failed-first-generation visibility and bounded
lock acquisition. No remaining production finding. Reviewer identified that keyword assertions
alone do not establish semantic replacement or unresolved decisions; an explicit synthetic
evidence artifact and manual semantic review are required before claiming real acceptance.

## Remaining real-model acceptance

Use a tool-capable real model; user selected OpenRouter as an available provider. Only the
external configuration path is needed; API keys must not appear in chat, repository or output.

```powershell
$env:ENGINEERING_MEMORY_MODELS_LLM_ENV = 'C:/Users/you/.config/engineering-memory/openrouter.env'
$env:ENGINEERING_MEMORY_MODELS_EVIDENCE = 'C:/Users/you/.config/engineering-memory/synthetic-models.json'
.venv/Scripts/python deploy/hindsight/e2e.py
```

This selects both real-model scenarios and rejects nonpassing/skipped results. It does not run
the fixture-only deliberate-failure case. Inspect the saved synthetic initial/refreshed/unresolved
responses: PostgreSQL must be the replacement for SQLite, jade must supersede cobalt, and neither
Rust nor Go may be claimed settled. Record the tested model, actual command/status, supporting
document IDs and those semantic judgments here. Do not mark acceptance complete from words alone.
