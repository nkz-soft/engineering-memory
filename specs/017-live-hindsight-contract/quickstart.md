# Quickstart Validation Guide

This is a design-stage guide. The test overlay and dedicated cases are planned, not implemented yet.

## Prerequisites

Python 3.13 through uv, Docker Compose, capacity for the pinned engine and its local models, and network access for initial image/model downloads. No private exports or paid API credentials are needed for the planned CI fixture stack.

## Existing baseline

```powershell
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Offline pytest currently skips live tests unless explicitly enabled.

## Planned live validation

The implementation will add a test-only Compose overlay under deploy/hindsight and document its exact startup command here. Start an isolated project extending service.yaml, with the deterministic extraction fixture and an isolated volume; wait for readiness before running:

```powershell
$env:ENGINEERING_MEMORY_LIVE_STORE = '1'
$env:ENGINEERING_MEMORY_LIVE_STORE_URL = 'http://127.0.0.1:8889'
uv run pytest tests/integration/test_hindsight_store.py -ra
```

The selected path may be split into a dedicated suite during implementation; update this guide and CI together. Configure the overlay to bind the corresponding loopback port.

Expected: all five contract families execute, no skips, every mismatch identifies its architecture section, scratch banks are removed. Run twice to demonstrate isolation. Run the dedicated CI job and inspect its actual result before claiming CI verification. Always bring the isolated project down with volumes after a run.

Negative controls must demonstrate failed expectations for duplicate/stale facts, extra extraction calls, incorrect tag membership, import-time substitution and unexpected success on an untouched bank. Verify fixture unknown-request rejection and finite timeout handling offline before live runs.
