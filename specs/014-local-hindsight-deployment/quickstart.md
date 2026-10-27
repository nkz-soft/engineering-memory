# Quickstart Validation: Local Hindsight Deployment

This guide describes Phase 2 validation. Deployment files and smoke code are not present in the planning commit; the commands below are future acceptance steps, not claimed results.

## Prerequisites

Use the approved worktree with Python 3.13, uv, Docker Engine/Desktop and Compose v2 Linux-container support. The existing LiteLLM proxy must be reachable from the engine container and have a configured structured-extraction alias. Obtain its URL/key externally. Reserve a free host API port and enough image/model disk/RAM resources documented by the implementation guide. No real export, production bank or hosted Hindsight account is needed.

## Configure and start

Follow docs/development/local-hindsight.md for PowerShell/POSIX environment setup. Set container-side HINDSIGHT_API_LLM_BASE_URL, HINDSIGHT_API_LLM_MODEL and key if needed. A keyless proxy may require an explicitly documented nonsecret client placeholder. Do not paste credentials into commands committed to the repository or print resolved configuration.

```text
docker compose -f deploy/hindsight/compose.yaml config --quiet
docker compose -f deploy/hindsight/compose.yaml pull
docker compose -f deploy/hindsight/compose.yaml up -d --wait --wait-timeout 300
```

Expected: fixed image/digest, healthy service, API published only on loopback, private embedded database and persistent named volume. The Compose health check must be implemented for --wait to establish readiness. Document initial preparation/model-download time separately from the bounded readiness wait.

Configure the host-side existing ENGINEERING_MEMORY_HINDSIGHT__BASE_URL, optional TOKEN and the required ENGINEERING_MEMORY_LLM__BASE_URL/key settings. The engine's container proxy address may differ from the host application's proxy address. The default local engine has no authentication; a separately secured engine uses its own token, never the proxy key.

## Prove extraction and recall

```text
uv run python -m engineering_memory.memory.hindsight.smoke
```

Expected: a fresh engineering-memory-smoke-UUID bank, successful completed retain, expected fact recalled, scoped cleanup and zero exit. Repeat and confirm a different bank. Record the run's metadata window and separately observe successful extraction at the existing proxy, with alias/time/request identifier/status only. No body or authorization logging. Missing proxy evidence means live acceptance is incomplete even when smoke passes.

For persistence inspection, use the implementation's --keep-scratch option, stop normally and restart, and verify that run's synthetic document is still present. Cleanup must remain restricted to the generated bank. Normal `docker compose -f deploy/hindsight/compose.yaml down` preserves the volume. Destructive reset is a separate guide step and must target only this Compose project's data volume.

## Failure checks

| Scenario | Expected result |
|---|---|
| Missing proxy URL/alias | Clear failure before apparently ready deployment |
| Wrong proxy key, unsupported alias or unavailable proxy | Smoke fails, no false extraction claim |
| Reachable health but failed retain/recall | Smoke fails at the actual stage |
| Empty/wrong/malformed recall | Nonzero; expected-fact assertion not bypassed |
| Pending operation or deadline exceeded | Nonzero; HTTP acceptance is not completion |
| Cleanup failure | Report separately, identify only scratch bank, no production target |
| Secret canaries in failure responses/settings | No exposure in stdout/stderr/logs |

Use offline unit tests to cover these failures; do not deliberately misconfigure real credentials in public CI logs.

## Offline validation after implementation

```text
uv run pytest tests/unit/test_hindsight_smoke.py tests/structure/test_hindsight_deployment.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv lock --check
git diff --check
```

Ordinary tests require no Docker, proxy or credentials. Compose behavior checks run only when explicitly available; live acceptance is its own recorded step. Verify pinned OpenAPI and hand any architecture §9 route discrepancy to #16 without claiming the production adapter contract was tested.

## Planning baseline

`uv run pytest -q --tb=short -rs` on main aee772b: **1571 passed, 4 skipped in 50.94s**. The skips are two unsupported fake-store failure hooks and two Windows symlink-permission cases. This baseline does not verify a live deployment.
