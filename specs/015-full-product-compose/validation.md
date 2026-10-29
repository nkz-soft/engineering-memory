# Validation — issue #55 infrastructure increment

Date: 2026-10-29. Host: Windows PowerShell, Docker Desktop Linux daemon,
Docker Compose v5.6.0, Python 3.13.15. Main baseline: e65afa2.

## Executed checks

| Command | Result |
| --- | --- |
| `uv run pytest -q` | **1653 passed, 4 skipped**, 49.19s after all code-review fixes. No product live pass claimed. |
| `uv run ruff check .` | All checks passed. |
| `uv run ruff format --check .` | 314 files already formatted. |
| `uv run pytest tests/unit/test_product_runner.py tests/structure/test_product_deployment.py tests/structure/test_hindsight_deployment.py -q` | 35 passed after reviewer regression fixes. |
| `.venv/Scripts/python.exe deploy/product/run.py config` | Exit 0, `OK: config`, no provider calls. |
| `.venv/Scripts/python.exe deploy/product/run.py config --external` | Exit 0, `OK: config`, no provider calls. |
| `.venv/Scripts/python.exe deploy/product/run.py e2e --live` | Exit 77, `SKIPPED: product prerequisites #16/#17/#19/#21/#23/#24 are unavailable`. No live resources created. |
| `docker compose -p engineering-memory-product-dev -f deploy/product/compose.yaml --profile tools --profile internal config --quiet` | Exit 0 with a synthetic nonsecret `PRODUCT_PROXY_KEY`. Confirms profile selection for documented rebuild. |
| `docker build -t engineering-memory:issue55-validation .` | Exit 0; built image sha256:6d60875bc425af2db0456f5045100a6189e74f0d6b982677bc08fbfc5e7c1a77. |
| `docker run --rm engineering-memory:issue55-validation --version` | Exit 0, `engineering-memory 0.1.0`. |
| Fresh anonymous volume write check below | Exit 0; UID 10001 can write both mounts. Anonymous volumes removed by `--rm`. |
| `git diff --check` | Passed. |

Volume check (synthetic data only):

```text
docker run --rm -v /var/lib/engineering-memory/archive -v /var/lib/engineering-memory/state --entrypoint python engineering-memory:issue55-validation -c 'import os,pathlib; assert os.getuid()==10001; roots=[pathlib.Path("/var/lib/engineering-memory")/name for name in ("archive","state")]; [(root/"write-check").write_text("synthetic") for root in roots]; print("UID 10001 can write both fresh anonymous volumes")'
```

## Test-first and independent review

Initial infrastructure tests failed because Compose/capability files were absent.
Runner tests failed because the runner and owned storage paths were absent.
Additional failures reproduced shared image naming and missing nested environment
exclusions. Independent review identified CLI credential-skip ordering, blank
credential stop/reset and Linux host DNS issues. Each received a failing regression
test followed by the passing focused/full runs above. Final documentation review
also caught and corrected the internal profile missing from the rebuild command.

An initial sandboxed `uv sync --locked` failed to persist uv interpreter-cache
files. The first sandboxed pytest run encountered Windows temporary-directory
permission errors and was interrupted. Checks were rerun with normal cache/temp
access; no code or test change was used to hide those environment errors.

LiteLLM release tag variants were not available in the registry.
`docker buildx imagetools inspect ghcr.io/berriai/litellm:main-stable --format '{{json .Manifest}}'`
resolved the multiarchitecture digest now pinned in Compose. No floating proxy
image is used at runtime. Route configuration follows the official
[LiteLLM configuration guide](https://docs.litellm.ai/docs/proxy/docker_quick_start),
[logging controls](https://docs.litellm.ai/docs/proxy/logging) and
[production configuration](https://docs.litellm.ai/docs/proxy/prod).

## Outstanding acceptance

- Actual bank/retain-mission provisioning, import/status/MCP bindings and product
  E2E scenario: blocked by upstream capabilities; T008/T011 remain unchecked.
- Real provider-backed extraction and failure behavior, product retrieval,
  provenance/archive checks, unchanged re-import, full-stack persistence and
  concurrent live cleanup: not run; T012 remains unchecked.
- Windows full-stack startup and Linux full-stack/runtime validation: outstanding.
  Docker image build/runtime permission checks on a Windows-hosted Linux daemon
  do not establish Linux host networking or full-product platform acceptance.
- No provider credentials or private conversation payloads were used. Dependency
  services were not started with fake credentials merely to claim a live pass.

The draft PR is the infrastructure-first increment allowed by FR-013, not a claim
that #55's full-product acceptance is complete. Do not merge/close the issue until
the remaining product integration and live acceptance work is done.
