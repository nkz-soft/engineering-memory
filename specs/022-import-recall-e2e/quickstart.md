# Quickstart validation

These commands describe the intended implementation; this planning commit adds no executable gate.

Prerequisites: Python 3.13, uv, Docker daemon, ability to pull the existing pinned engine and build/run the synthetic extraction fixture. No model credentials or real conversation exports are required.

```powershell
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python deploy/hindsight/contract.py
uv run python deploy/hindsight/e2e.py
uv run python deploy/hindsight/e2e.py
```

Expected: offline tests pass with explicit live skips; each required live runner executes its selected cases without skips. Each end-to-end run begins empty, recalls the decision with complete evidence, and removes its resources. The second run is independent of the first.

During implementation, record a failing run before adding the harness, then the successful run. Run negative controls for provenance/tag omissions and a real wire-timestamp omission; each must demonstrate an assertion failure. Confirm a missing or skipped required case fails the report guard. Verify failed startup and failed assertions still trigger cleanup. Do not invoke destructive controls against an existing user bank.
