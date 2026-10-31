# Quickstart validation guide

The CLI is implemented. Run the following checks against synthetic history only.

## Prerequisites

Use Python 3.13 and `uv sync --locked`. Configure local paths and remote endpoints using existing `.env.example` instructions. Keep secrets in the environment. Use synthetic fixture exports and scratch storage for all validation. Start the documented local Hindsight instance with extraction configured through the existing proxy setup. Live validation requires an available instance and credentials; record a blocker instead of claiming skipped tests passed.

## Local checks

```powershell
uv run pytest tests/unit tests/contracts tests/structure
uv run pytest tests/integration
uv run ruff check .
uv run ruff format --check .
uv run engineering-memory --help
uv run engineering-memory --version
uv run engineering-memory provision --help
uv run engineering-memory import --help
uv run engineering-memory status --help
```

New command tests must use Typer CliRunner, observe failures before implementation, and inject fake memory only for offline suites. Existing live integration controls remain opt-in. For the live command workflow, start the isolated contract stack, then run:

```powershell
docker compose -p cli-validation -f deploy/hindsight/compose.contract.yaml up -d --wait
$env:ENGINEERING_MEMORY_LIVE_CONTRACT = '1'
uv run pytest tests/integration/test_operator_cli.py::test_live_commands -q
Remove-Item Env:ENGINEERING_MEMORY_LIVE_CONTRACT
docker compose -p cli-validation -f deploy/hindsight/compose.contract.yaml down --volumes
```

The test uses a unique scratch bank, temporary local storage, and synthetic extraction.
It provisions, imports, skips unchanged history, replays with force, inspects status,
and recalls the synthetic fact. The scratch bank and disposable stack are removed.

## Fixture and live workflow

Generate a synthetic export with the existing test helpers into ignored `data/cli-fixture/`; point archive/state settings to separate scratch paths. Do not commit exports or environment files.

```powershell
uv run engineering-memory provision --json
uv run engineering-memory import --export data/cli-fixture/conversations.json --json
uv run engineering-memory import --export data/cli-fixture/conversations.json --json
uv run engineering-memory status --json
uv run engineering-memory import --from-archive --force --json
```

Expected: provisioning verifies mission; first import archives and retains each valid item; second import skips all unchanged successes with zero extra retain calls; status shows imported/failed latest records without persistent skips; forced archive replay works with the export removed. Repeat each operational command without --json and check readable output. Check live retention using existing contract-test helpers and known synthetic facts.

## Failure and offline checks

Run invalid selector combinations (exit 2), malformed/mixed inputs and unavailable services (exit 1), empty inputs (exit 0), changed/failed reruns and interrupts (exit 130). Parse structured stdout as one object; assert synthetic secrets in input/exception text appear in neither stdout nor stderr. Inspect status with remote settings absent and network forbidden; absent DB stays absent, existing DB/archive hashes stay unchanged. A successful inspection of stored failures exits 0. Use synthetic fixtures only, and capture exact executed commands/output in the implementation report.
