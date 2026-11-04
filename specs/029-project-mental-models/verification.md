# Verification: Project mental models

Date: 2026-11-04. Feature: issue #30, branch `029-project-mental-models`.
Base implementation checkout: `90261a5`; planning commits `8e4fbed`, `ec7a149`.
Initial implementation commit: `d465120`. PR: https://github.com/nkz-soft/engineering-memory/pull/72.

## Current result

Implementation, offline regression checks, isolated live protocol/lifecycle gate, existing
engine contract gate and real-model acceptance pass. The operator's first real-model run
exposed speculative rationale despite passing topic checks. Grounding instructions were
tightened, the observed output failed a new regression check, and a fresh real-model run
passed with manual semantic review. Fixture output is not used as evidence of model quality.

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
| `.venv/Scripts/python -m pytest -q --tb=short` | Final regression: 2134 passed, 42 skipped; 120.14 seconds |
| `.venv/Scripts/python -m ruff check .` | All checks passed |
| `.venv/Scripts/python -m ruff format --check .` | 531 files already formatted at final check |
| `git diff --check` | Passed |
| `.venv/Scripts/python deploy/hindsight/e2e.py` | Final credential-free gate: 36 passed, no skips; 75.32 seconds for pytest |
| `.venv/Scripts/python deploy/hindsight/contract.py` | 9 passed, no skips; 13.18 seconds for pytest |
| `.venv/Scripts/engineering-memory --help` | New models command listed, exit 0 |
| `.venv/Scripts/engineering-memory models refresh --help` | Project/kind/JSON options listed, exit 0 |

Normal-suite skips are opt-in live cases; the required live suites above executed without skips.
The final full regression and live model gate include the stricter synthesis instructions and
the supplemental speculative-qualifier check. The unchanged base engine contract gate was
not rerun for this prompt-only correction; its prior 9-case pass remains recorded above.
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

## Real-model acceptance

Provider: OpenRouter through the OpenAI-compatible provider; model `openai/gpt-4.1-mini`.
Only the four selected backend LLM settings were read from the external file. No API key,
external secret file or private history was printed or committed.

```powershell
$env:ENGINEERING_MEMORY_MODELS_LLM_ENV = 'C:/Users/Nicko/.config/engineering-memory/openrouter.env'
$env:ENGINEERING_MEMORY_MODELS_EVIDENCE = 'D:/Projects/open-source/nz/hermes-memory/.claude/worktrees/model30-corrected-evidence.json'
.venv/Scripts/python deploy/hindsight/e2e.py
```

Final real-model result: **2 passed, no skips, 101.50 seconds**. The fixture-only deliberate-failure
case is separately covered by the default 36-case gate. The operator independently ran the
default gate (36 passed in 45.13 seconds) and the initial real-model gate (2 passed in 101.95 seconds).

The first output correctly handled supersession but invented SQLite scaling/performance motives
and component interactions. The new speculative-qualifier assertion failed on that actual saved
decisions response before the prompt correction. This detector is intentionally narrow: it may
reject legitimate negations and does not establish semantic correctness by itself.

Manual review of [the corrected synthetic evidence](semantic-evidence.json) establishes:

- Initial architecture combines the cobalt retry-isolation and amber admission conversations;
  supports are chatgpt:architecture and chatgpt:gateway, with no beta/untagged decoy facts.
- Refreshed architecture, stack and decisions explicitly replace cobalt with jade and SQLite
  with PostgreSQL. All cite chatgpt:replacement; historical supports remain inspectable.
- The refreshed stack keeps Python 3.13 and the amber gateway instead of treating the named
  replacements as removal of unrelated components.
- The refreshed summaries state that replacement rationale and component interactions are not
  recorded, rather than asserting unsupported SQLite scaling/performance reasons or routing flows.
- The unresolved response explicitly says neither Rust nor Go is accepted and cites only
  chatgpt:proposals. It does not silently settle one option.

Evidence SHA-256: `a964041bf3b525c4229542490a1b0c2ab346663f781de81a67e3954e9e1e9bb4`.
This is acceptance on a small synthetic corpus, not a claim of universally hallucination-free
generation. References establish inspectable grounding, not that every generated sentence is
entailed. The broader quality evaluation work remains #31.
