# Quickstart validation: Ingestion pipeline

Implementation-phase guide; tests below are planned and do not exist yet.

## Prerequisites

Python 3.13 and uv; run from the issue worktree. Fixtures are synthesized. No engine credential or external service is needed for these scenarios.

## Commands after implementation

```powershell
uv sync --locked --extra dev
uv run pytest tests/unit/test_ingestion_pipeline.py tests/unit/test_ingestion_report.py tests/unit/test_enrichment.py
uv run pytest tests/contracts/test_pipeline.py tests/integration/test_ingestion_pipeline.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Expected: focused suites pass, existing suites remain green (live infrastructure tests follow their documented opt-in requirements), and lint/format pass. Record actual outputs during implementation, including any skipped integration gates.

## Scenarios

1. Three synthetic records with a recoverable malformed middle record: two imported, one failed with available native id, safe error and UTC time; partial_success.
2. Run again: two skipped, failed item still attempted, successful state unchanged. Change content or use force: affected items process again under the same document ids.
3. Ordered recording memory fake checks archived original and sanitized normalized form already exist when retain is invoked. Synthetic secret must appear only in local original bytes.
4. Inject archive failure: no retain for that item; next item proceeds. Inject retain/state failure: report failed, retry uses stable identity.
5. Empty and all-skipped runs: success. All failed or unavailable source before progress: failure. Terminal source failure after a successful item: partial_success.
6. Inspect reports and captured logs for synthetic secret sentinels; inspect provenance for original time, correct source/project/type tags and importer version. Replay archived originals through existing archive source and verify they can be processed again.

Report fields and state transitions: [data-model.md](data-model.md). Ordering and failure contract: [contracts/pipeline.md](contracts/pipeline.md).
