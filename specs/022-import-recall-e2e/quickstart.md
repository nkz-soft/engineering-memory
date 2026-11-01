# Quickstart validation

Prerequisites: Python 3.13, uv, a running Linux Docker daemon, access to pull the existing pinned engine and Python fixture image. No model credentials or conversation exports are required. Startup can take several minutes while local embedding/reranking models load.

```powershell
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python deploy/hindsight/contract.py
uv run python deploy/hindsight/e2e.py
uv run python deploy/hindsight/e2e.py
```

The offline suite explicitly skips live cases. The required `Live import and recall` CI job invokes e2e.py, provisions a fresh stack through testcontainers, and refuses skipped, missing, duplicate or nonpassing required cases.

Three live cases prove: the real provision/import/status CLI can recall a decision; the real pipeline preserves populated repository/user context and enforces each tag namespace; and removing the actual retain timestamp fails the temporal-grounding assertion even though historical metadata remains. Offline controls reject omitted provenance fields, each required tag, timestamps and decision content.

The CLI has no repository/user arguments. Its case expects absent repository and the three required tags; the supplementary pipeline case supplies a known repository and optional user tag. Both use real parsing, sanitization, classification, enrichment, archive, state and live memory adapters.

The outer runner bounds startup and tests to 1020 seconds and reserves time to reap pytest. Cleanup has its own 90-second deadline and selects only the exact run label. It attempts remaining resources after individual removal failures and returns failure if cleanup is incomplete. A worker timeout, unavailable Docker/engine or malformed JUnit report cannot pass. Containers, anonymous volumes, the isolated network and temporary local state are disposable; never target a user bank for omission controls.

See [verification.md](verification.md) for executed commands and actual outcomes. Deterministic extraction verifies orchestration and real-engine retrieval; external-model quality is separate evaluation work.
