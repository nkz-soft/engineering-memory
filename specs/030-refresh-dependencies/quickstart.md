# Validation guide

## Prerequisites

Use a disposable checkout, Docker with Compose and Buildx, PowerShell, the candidate Specify CLI, and the configured proxy credentials via environment variables. Use synthetic data and independent Compose project names, ports and volumes.

## Deployment

1. Inspect each candidate image with `docker buildx imagetools inspect <image:tag@digest>` and confirm Linux amd64 and arm64. Resolve both stacks with `docker compose -f deploy/hindsight/compose.yaml config --quiet` and `docker compose -f deploy/product/compose.yaml config --quiet`, supplying their documented environment and overlays.
2. Run `uv run python deploy/hindsight/contract.py` and `uv run python deploy/hindsight/e2e.py`. For the standalone path, start `deploy/hindsight/compose.yaml` with `up -d --wait --wait-timeout 300` and run `uv run python -m engineering_memory.memory.hindsight.smoke` with the environment from [Local Hindsight](../../docs/development/local-hindsight.md). For the product path, use `docker compose -p <unique> -f deploy/product/compose.yaml -f deploy/product/compose.dev.yaml --profile internal up -d --wait --wait-timeout 300 hindsight litellm` and point the same smoke command at the product loopback endpoint. Correlate each request with redacted proxy evidence. Record which configuration each command exercised.
3. Seed a disposable old-version deployment with a synthetic fact and recall it. Copy its persisted state using the supported backup/restore procedure with a consistent database snapshot. Start the candidate on the copy, verify readiness, recall the original synthetic fact and run a new retain/recall round trip. Keep the baseline available until verification ends.

## Specification workflow

Record `specify version`. In a scratch checkout, run the migrated PowerShell specification, planning and task workflow with the Claude skills. Check the next sequential feature number, branch and feature directory, and review the generated diff for preserved customizations. Exercise task-to-issue mapping twice with the same task ID and confirm it resolves to the same issue.

## CI and package

Run `uv --version`, `uv python install`, `uv sync --locked`, `uv run python --version`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest`. Build with `docker build -t engineering-memory:issue-73 .` and run `docker run --rm engineering-memory:issue-73`. Record builder Python and uv versions and run `docker run --rm --entrypoint python engineering-memory:issue-73 --version` for the runtime patch.

Verify the hosted scan job checks out full history and the fixture returns exit 42 in the existing negative-control step. Record commands, outcomes and any candidate held back.
