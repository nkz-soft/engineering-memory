# Quickstart Validation Guide

This is a plan for Phase 2. Adapter tests and implementation do not exist yet.

The raw engine compatibility experiment now exists (adapter tests do not):

```powershell
$env:ENGINEERING_MEMORY_LIVE_STORE = '1'
uv run pytest tests/integration/test_hindsight_store.py -q --tb=short
```

Default engine URL is http://127.0.0.1:8889; override with
ENGINEERING_MEMORY_LIVE_STORE_URL. Uses only generated synthetic scratch banks
and deletes its bank on exit. Without opt-in it skips. As of 2026-10-30 the
single-item case passes and the multipart case fails HTTP 400; decision-needed.md
records the blocking contract conflict. These are engine experiments, not
product E2E or adapter completion.

## Offline verification after implementation

From the feature worktree, with Python 3.13 and uv:

```text
uv sync --locked
uv run pytest tests/contracts tests/unit tests/structure
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Expected: concrete adapter passes reusable memory contract; transport tests prove exact mapping, failure handling, pending UUID reuse and lossless multipart delivery. Graph tests reject direct/indirect implementation imports by production consumers. Capture red then green evidence during each implementation step.

## Real pinned engine

Follow ../../docs/development/local-hindsight.md with operator-supplied proxy settings. Never paste environment values into reports. Provision a uniquely named synthetic test bank and mission; never run destructive fixtures against engineering-global.

Phase 2 must document its exact opt-in environment switch and runnable integration command once the fixture exists. Test paths, async completion/idempotency, timestamps, strict tag filters, provenance, changed-content replacement and a multipart refresh. Recall synthetic facts from both ends under one document identity. Confirm reused operations do not repeat extraction through backend operation evidence.

Record pinned version/digest, commands, results and any unavailable Docker/proxy prerequisites. Missing live validation is an unmet completion gate, not a passing test. Remove only fixture-owned scratch data.
