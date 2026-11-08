# Verification

## Offline

- `.venv/Scripts/python.exe -m pytest -q --basetemp data/test-reflect-full-final2 --tb=short` reported 2,197 passed and 44 skipped.
- `.venv/Scripts/python.exe -m pytest -q --basetemp data/test-evaluator-regressions tests/integration/test_recall_evaluation.py tests/integration/test_reflect_evaluation.py --tb=short` reported 19 passed and one skipped. Windows did not grant directory symlink creation for that case.
- `.venv/Scripts/ruff.exe check .`, `.venv/Scripts/ruff.exe format --check .`, and `git diff --check` passed.
- The test-first runs caught the absent read methods, MCP route, and evaluator command. The existing recall CLI's synthetic server needed to implement the new route for its stdio startup. The corrected full run passed.

## Pinned engine

The isolated Compose stack exposed Hindsight 1.2.0. Its OpenAPI described the bank-scoped reflect route, the empty object for `include.facts`, and nullable provenance fields on evidence. [Pinned API source](https://github.com/vectorize-io/hindsight/blob/v1.2.0/hindsight-api-slim/hindsight_api/api/http.py)

With `ENGINEERING_MEMORY_LIVE_E2E=1` and `ENGINEERING_MEMORY_LIVE_STORE_URL=http://127.0.0.1:18891`, `.venv/Scripts/python.exe -m pytest -q --basetemp data/test-reflect-pinned-green tests/integration/test_reflect_live.py --tb=short --show-capture=no` reported one passed. The test retained synthetic records, verified evidence fields and project scoping, exercised MCP over stdio, opened both cited records, and verified that an answer without a matching archive record was withheld. The test model is deterministic and demonstrates protocol behavior.

- With the same engine URL plus `ENGINEERING_MEMORY_LIVE_MODELS=1` and `CONTRACT_FIXTURE_URL=http://127.0.0.1:18892`, `.venv/Scripts/python.exe -m pytest -q --basetemp data/test-reflect-live-final tests/integration/test_reflect_live.py tests/integration/test_import_recall_e2e.py tests/integration/test_project_models_live.py --tb=short --show-capture=no` reported 36 passed. A broad fixture schema match initially masked the deliberate failed-refresh case. Restricting the new schema branch to the synthetic reflect contract query restored the expected failure behavior.

## Accumulated corpus

`docker compose ls -a` and `docker volume ls` showed stopped #32 synthetic benchmark services and saved development engine volumes. The configured connector archive held three prior acceptance records. The saved product engine volume had no corresponding Compose archive volume, and the configured connector did not identify a matching archive for the accumulated corpus.

The live case set, paired measurements, and reviewed aggregate results remain open. See the [operator guide](../../docs/operations/reflect-evaluation.md) for prerequisites and the review rubric.
