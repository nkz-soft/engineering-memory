# Adapter validation and use

The adapter is HindsightStore in memory/hindsight/store.py. Construct with
HindsightSettings and use close() or a context manager. An injected httpx.Client
remains caller-owned. Calls accept already sanitized EnrichedConversation;
archiving and sanitization belong to the upstream pipeline.

One complete conversation is sent as one async replace item. Extraction chunking
belongs to the engine. Default complete request cap: 8 MiB; override constructor
max_request_bytes deliberately. Larger input is rejected before network I/O.
Default HTTP timeout: 30 seconds, overall extraction completion: 240 seconds.

## Offline checks

```text
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Shared adapter contracts use a stateful wire fixture. Unit tests cover exact
payload, source time, provenance, strict scope/limits, malformed responses, error
translation, pending UUID replay, deadlines and size limits. Structure tests
reject direct/relative/transitive production dependencies on the adapter.

## Real engine

Use docs/development/full-product.md. The ignored deploy/product/.env holds the
provider route/key and the network proxy. OpenRouter must use HTTPS_PROXY or
ALL_PROXY; the current Docker Desktop host proxy is reachable through
host.docker.internal. Do not bypass OpenRouter with NO_PROXY. Never print resolved
Compose configuration or provider responses containing secrets.

```text
uv run python deploy/product/run.py dependencies
```

Then PowerShell:

```powershell
$env:ENGINEERING_MEMORY_LIVE_STORE = '1'
uv run pytest tests/integration/test_hindsight_store.py tests/contracts/test_hindsight_store_passes_the_contract.py -q --tb=short
```

Default test URL is http://127.0.0.1:8889. Override with
ENGINEERING_MEMORY_LIVE_STORE_URL. Tests use generated scratch banks, synthetic
content, and cleanup. Local engine httpx clients disable environment proxies;
only LiteLLM provider traffic uses the network proxy. No production bank writes.
Without explicit opt-in live tests skip. These are engine/adapter contracts, not
product pipeline E2E, which belongs to the downstream product issues.

## Retry boundary

Exact retries after uncertain outcomes reuse the UUID in the same adapter
instance. Confirmed success and changed payload create fresh operations; force
and A-to-B-to-A therefore work. The bounded pending map is not durable across
process restart. Cross-process operation coordination and backoff belong to #20.
Retain returns success only after completed extraction, never mere acceptance.
