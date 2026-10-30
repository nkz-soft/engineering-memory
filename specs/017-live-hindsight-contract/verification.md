# Verification: Live Hindsight Contract

## Test-first evidence

- Fixture protocol tests were written first: pytest collection failed with ModuleNotFoundError for tests.integration.hindsight_contract. After implementation: 4 passed.
- Runner/report tests were written first: collection failed with ModuleNotFoundError for deploy.hindsight.contract. After runner and CI changes: 20 passed including workflow checks.
- Live assertions exposed the initial extraction protocol mismatch; strict schema mode aligned the fixture with the pinned provider. Unknown requests remain failures.
- A clean run exposed startup model probes outside the extraction protocol and an incorrect hard-filter assumption about temporal spreading. Startup verification is disabled in the test-only stack; the temporal assertion checks original-time priority as documented in research.md.

## Commands and observed outcomes

- `.venv/Scripts/python -m pytest -q --tb=short`: 1751 passed, 27 opt-in tests skipped (before the seven additional mutation controls).
- `.venv/Scripts/python -m pytest tests/unit/test_contract_llm.py tests/unit/test_contract_runner.py tests/unit/test_live_contract_controls.py tests/structure/test_ci_workflow.py -q`: 31 passed, including all seven mutation controls.
- `.venv/Scripts/python -m ruff check .`: All checks passed.
- `.venv/Scripts/python -m ruff format --check .`: 359 files already formatted.
- `git diff --check`: passed.
- `.venv/Scripts/python deploy/hindsight/contract.py`: clean isolated run, 9 passed in 14.28 seconds; zero skips, report accepted, exit 0, all Compose resources removed.

Windows sandbox blocked local sockets and pytest temp-directory creation; live and full-suite commands were run with approved elevated execution. No application behavior was changed to accommodate sandbox limits.

## Review

Independent review found a missing positive retry assertion and missing per-family mutation controls. Both were fixed and re-reviewed: no remaining substantive findings.

## Limits

Synthetic extraction does not validate paid-model quality. The real pinned engine performs extraction orchestration, persistence, async idempotency, embedding, reranking and recall. The temporal contract is original-date preservation and temporal-arm priority, not generic chronological sorting or exclusion of all out-of-window neighbours.

Second independent clean runner invocation: 9 passed in 13.57 seconds, zero skips, report accepted, exit 0 and all Compose resources removed.
