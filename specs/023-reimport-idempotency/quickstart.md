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
