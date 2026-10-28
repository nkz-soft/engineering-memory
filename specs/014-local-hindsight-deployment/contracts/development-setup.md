# Contract: Local Hindsight Development Setup

## Deployment entry point

`docker compose -f deploy/hindsight/compose.yaml up -d`

Before startup, supply HINDSIGHT_API_LLM_BASE_URL, HINDSIGHT_API_LLM_MODEL (proxy alias), and HINDSIGHT_API_LLM_API_KEY when required. Guide examples must handle both PowerShell and POSIX shells without secret literals. Compose rejects missing URL/alias; if the pinned provider requires a nonempty key for a keyless proxy, require a documented nonsecret placeholder. Do not dump interpolated Compose configuration or shell traces.

Normal shutdown: `docker compose -f deploy/hindsight/compose.yaml down`. It preserves the project's named data volume. Reset is a separate explicitly destructive documented action, never part of startup/readiness/smoke.

## Smoke entry point

`uv run python -m engineering_memory.memory.hindsight.smoke`

Positive timeout option default: 180 seconds. Readiness setup default: 300 seconds. Optional `--keep-scratch` retains only this run's generated bank for inspection. No arbitrary bank/content/input-file option exists. Use existing load_settings for environment resolution; do not create another application environment reader.

Exit zero only when engine retain has completed and recall contains the expected synthetic answer, with cleanup successful or intentionally kept. Print run ID, generated bank ID, UTC window and stage outcomes. Output must explicitly distinguish HTTP smoke success from operator-confirmed proxy routing evidence. Fail with nonzero for configuration, HTTP, JSON/schema, extraction, recall mismatch, deadline or requested cleanup failures. Never print raw client exceptions, endpoint credentials, bodies or unwrapped settings secrets.

HTTP implementation is engine-specific and belongs only to memory/hindsight. Use httpx with a configurable transport for offline tests. Engine token goes only to engine requests; the proxy key is never forwarded by smoke. Disable environment-derived HTTP proxies for these local API calls. Bound every request by remaining monotonic budget and do not retry retain blindly.

## Pinned HTTP surface to verify during implementation

| Stage | Current upstream candidate |
|---|---|
| Readiness | GET /health or /health/ready, verified for pin |
| Schema/version evidence | GET /openapi.json and image identity |
| Retain | POST /v1/default/banks/{generated_bank}/memories with items and async=false |
| Recall | POST /v1/default/banks/{generated_bank}/memories/recall; verify results text |
| Queued completion, if encountered | GET /v1/default/banks/{generated_bank}/operations/{operation_id} |
| Cleanup | Delete only the generated bank using the pinned server's verified bank-delete route |

Current upstream route spellings differ from architecture §9. Verify actual pin behavior and document findings for #16; no silently changed production contract or claim that #16 is complete. If the live pin violates required architecture semantics, report it before production use.

## Live acceptance evidence

From a clean supported setup: image pin/digest, readiness, smoke expected-fact result, distinct scratch IDs across runs, metadata-only successful proxy observation, restart persistence under keep-scratch, loopback-only published API and no host DB port. A mock service is insufficient evidence of extraction or proxy routing.

The guide must explain how future host-run tests use existing settings and a scratch bank. Ordinary pytest remains offline. No real export is used. No access consumer is configured against this direct engine endpoint; ADR-008 remains binding.
