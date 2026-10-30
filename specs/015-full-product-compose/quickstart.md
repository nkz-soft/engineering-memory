# Validation quickstart (planned workflow)

This is a review guide for implementation, not a claim that the proposed services exist yet.

## Prerequisites

Linux Docker Engine or Windows Docker Desktop running Linux containers, Docker Compose, Python 3.13/uv for host checks, and externally supplied model route/credentials for live work. Product adapter/provisioner/pipeline/CLI/MCP and E2E prerequisites must land first. No real history fixture is needed.

## Offline validation

From repository root run:

```text
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

After implementation, run quiet Compose validation for dev, external-proxy and E2E variants with nonsecret sentinel inputs. Record final exact file/flag arguments in the operator guide. Expected: lifecycle/configuration tests pass without provider access; live tests report a named skip.

## Development acceptance

Follow the implemented guide's single startup command from a clean checkout. Verify required configuration failure before extraction, successful repeated initialization, synthetic import/status and MCP retrieval. Stop/start and verify archive, SQLite and engine persistence. Edit source, rebuild and exercise the change. Only the separate explicit reset may remove persistent development volumes.

## Live E2E acceptance

Use the implemented single opt-in E2E command with externally injected secrets. Record exact commands, exit statuses and safe summaries. Verify original/sanitized archives, real extraction completion, original time/provenance, expected fact and conversation via product MCP, unchanged re-import skip/no duplicates. Run two invocations concurrently while development remains running; compare ownership and verify cleanup leaves development/unrelated resources intact. Inject unavailable dependency, invalid route, extraction failure and timeout and verify bounded failure plus owned cleanup.

## Platform evidence

Planning only: Windows Docker Desktop validation outstanding; Linux validation outstanding; real provider-backed extraction outstanding. Missing credentials must be reported as skipped, not passing. The implementation PR must preserve outstanding items unless actually exercised.
