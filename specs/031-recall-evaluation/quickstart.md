# Validation guide — Recall evaluation

The experiment uses only the checked-in synthetic corpus.

## Verify the scorer and consumer path

```text
uv sync --locked
uv run pytest -q tests/unit/test_recall_evaluation.py tests/integration/test_recall_evaluation.py
```

Confirm coverage for complete, partial, and empty recall, wrong provenance, invalid inputs, transport errors, incompatible reports, and absence of response text in output.

## Run the live baseline and candidate

1. Prepare two disposable local Hindsight deployments with empty volumes and identical pinned engine, extraction model, and model settings. Follow the [self-hosted deployment guide](../../docs/development/local-hindsight.md) with a working extractor. Enable the bank configuration API for both instances so provisioning can apply the missions. Use the normal shared-bank name in each isolated instance. Point `ENGINEERING_MEMORY_HINDSIGHT__BASE_URL`, `ENGINEERING_MEMORY_ARCHIVE_ROOT`, and `ENGINEERING_MEMORY_IMPORT_STATE_PATH` at that run's own resources. Set `ENGINEERING_MEMORY_PROJECT_RULES_PATH` to the checked-in benchmark rules.
2. For baseline, provision normally. For the candidate, record a restrictive mission that omits a category represented in the corpus. In a disposable copy of the application at the same revision, replace only the packaged `src/engineering_memory/memory/hindsight/mission.txt` and run `provision` against the candidate instance. Verify both provisioning commands succeed and record the SHA-256 of the mission text applied in each. Keep the canonical package for both imports and scoring runs.
3. In each environment run `uv run engineering-memory import --source chatgpt --export evaluation/recall-v1/conversations.json --json`. Confirm the successful import count matches the corpus and that there were zero failures or skipped conversations before scoring. Wait for extraction to finish if the configured engine queues retention.
4. Create a profile JSON for each run and replace the example values with the actual engine version, public model identifier, and SHA-256 of the applied mission. Use a short identifier with letters, digits, periods, hyphens, or underscores for each label.

```json
{
  "run_id": "baseline",
  "engine_version": "1.2.0",
  "extractor_id": "example-model",
  "mission_sha256": "0000000000000000000000000000000000000000000000000000000000000000"
}
```

Run the evaluator once for each environment with the same benchmark manifest.

```text
uv run engineering-memory evaluate recall --benchmark evaluation/recall-v1/benchmark.json --profile BASELINE_PROFILE --output BASELINE_REPORT
uv run engineering-memory evaluate recall --benchmark evaluation/recall-v1/benchmark.json --profile CANDIDATE_PROFILE --output CANDIDATE_REPORT
uv run engineering-memory evaluate compare --baseline BASELINE_REPORT --candidate CANDIDATE_REPORT --output COMPARISON_REPORT
```

5. Confirm there are at least 30 outcomes in each report, all seven categories appear, both runs used the same input digests and retrieval settings, and the overall delta is nonzero. Document the category changes, exact public mission variant, engine and extractor identifiers, and any observed variation. If the score is unchanged, report the result and investigate extraction and matcher behavior before claiming the criterion is met.
6. Review the allowlisted metadata and commit the two JSON reports and comparison under `evaluation/recall-v1/results/`. Keep the environment files, archives, logs, and database files local. Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest` before review.

The [published baseline and candidate reports](../../evaluation/recall-v1/results/README.md) record the measured changes and the exact experimental settings.
