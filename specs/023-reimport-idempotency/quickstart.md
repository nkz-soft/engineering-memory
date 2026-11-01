# Quickstart: Validate re-import idempotency

Run from repository root after Phase 2 implementation. Prerequisites: Python 3.13, uv, Docker daemon and access to pinned container images. No external LLM credentials or private history are needed.

```powershell
uv sync --frozen --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python deploy/hindsight/contract.py
uv run python deploy/hindsight/e2e.py
```

The offline suite must pass assertion negative controls and runner completeness checks; live cases are explicitly skipped there.

The required E2E runner must report all prior required cases plus the unchanged, lost-state and changed-content cases with zero skips/errors/failures. Expected replay evidence: zero retain/extraction for unchanged; all members resubmitted without new documents after state loss; exactly the changed identity resubmitted for an edit. Recall verifies both controlled documents after every run. Repeat the E2E runner from clean resources and verify test-owned resources are removed.

These are planned validation commands, not results from this planning phase. See contracts/reimport.md for exact evidence requirements. No tasks or implementation are created until plan approval.

## Implementation verification (2026-11-01)

The implementation extends the existing live module with three replay cases and independent evidence controls. Production code and public contracts are unchanged.

- Red: new evidence tests failed before validators existed; three new required-case controls reported `DID NOT RAISE` before runner registration.
- Live red: `.venv/Scripts/python deploy/hindsight/e2e.py` returned 3 failed, 28 passed; all three replay scenarios failed because their harness was not implemented.
- Green: `.venv/Scripts/python -m pytest -q --tb=short` returned 1928 passed, 34 skipped in 85.05 seconds. Skips are opt-in live/platform cases; the required live gate executes its cases without skips.
- `.venv/Scripts/ruff check .`: all checks passed.
- `.venv/Scripts/ruff format --check .`: 429 files already formatted.
- `.venv/Scripts/python deploy/hindsight/e2e.py`: 31 passed in 16.34 seconds, including every required original and replay case.
- Independent read-only code review: no actionable findings. Recall completeness is intentionally scoped to the two-document deterministic scratch corpus.

Initial restricted-environment runs encountered Windows temporary-directory permission failures in existing runner tests. The complete suite above ran with normal temporary-directory access and passed without code changes for that environment restriction.
- `.venv/Scripts/python deploy/hindsight/contract.py`: 9 passed in 12.45 seconds; Compose removed the test containers, volume and network.
- Repeated `.venv/Scripts/python deploy/hindsight/e2e.py`: 31 passed in 16.73 seconds; both runner invocations completed successfully with cleanup.
