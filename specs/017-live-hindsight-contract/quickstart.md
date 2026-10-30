# Quickstart: Live Hindsight Contract

Prerequisites: Python 3.13, uv, Docker Compose, and network access for initial image/model downloads. No private history or paid-model credentials are needed.

From the repository root:

```powershell
uv sync --locked
uv run python deploy/hindsight/contract.py
```

The runner creates a unique Compose project, starts the canonical pinned engine with a synthetic extraction dependency, waits up to ten minutes for health, and runs exactly nine cases spanning all five contract families. It rejects skipped, missing or failed cases and always removes its containers, network and volume. The test subprocess has a seven-minute timeout; CI has a 25-minute job timeout. Scratch banks are deleted after each test as well.

Ports default to loopback 8889 (engine) and 8890 (fixture). For concurrent local runs:

```powershell
$env:CONTRACT_ENGINE_PORT = '18889'
$env:CONTRACT_FIXTURE_PORT = '18890'
uv run python deploy/hindsight/contract.py
```

Do not point this suite at an operator bank or production service. The runner supplies its own isolated URLs and ENGINEERING_MEMORY_LIVE_CONTRACT=1; ordinary offline pytest skips the nine live cases. The older ENGINEERING_MEMORY_LIVE_STORE opt-in remains separate.

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/unit/test_live_contract_controls.py tests/unit/test_contract_llm.py tests/unit/test_contract_runner.py
```

The seven mutation controls invoke the actual live assertion functions with wrong outcomes (stale facts, duplicate documents, extra extraction, leaked tag membership, substituted import time, wrong temporal priority and a successful untouched-bank read). Protocol tests reject unknown extraction requests; report tests reject skipped/incomplete/failed execution.

Temporal validation examines original dates and the temporal arm's priority with two centred windows, each around one original date. Temporal spreading may include out-of-window neighbours, and final semantic recall is not promised to be chronologically sorted. The LLM fixture does not measure model extraction quality; embeddings, reranking, queueing, persistence and recall remain real engine behavior. Startup LLM probes and automatic observation consolidation are disabled because their prompts are outside this extraction-only fixture's contract.
