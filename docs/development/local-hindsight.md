# Local Hindsight through an existing LiteLLM proxy

This development setup starts a separate, self-hosted Hindsight instance. Its extraction calls use your existing LiteLLM proxy; embeddings and reranking run locally in the full image. Only the API is published, on host loopback. The bundled UI and embedded database have no published host ports.

This is infrastructure for future contract tests and the memory adapter. It does not implement import/search commands or configure Hermes. Bank provisioning is an explicit CLI step described below. Consumers continue to use engineering-memory's access surface (ADR-008).

## Prerequisites

- Docker Engine with Compose v2 on Linux, or Docker Desktop with Linux containers on Windows/macOS. Start the daemon first. Confirm `docker version` reports a server and `docker compose version` succeeds.
- Python 3.13 and uv for the smoke command. Run `uv sync --locked` in this checkout.
- An existing LiteLLM OpenAI-compatible proxy and an alias capable of structured extraction. Its URL, key and alias belong to the operator. This guide does not deploy a proxy or select the underlying model.
- Disk space for the full image (upstream documents approximately 9 GB on AMD64) plus its data/model cache. Upstream recommends about 2 GB RAM for the API; allow additional headroom for embedded PostgreSQL and Docker. CPU inference is adequate for the synthetic check. Initial image/model preparation needs network access and can take several minutes.
- An unused loopback port, 8888 by default. Change `HINDSIGHT_DEV_PORT` if necessary.

The image is pinned in [compose.yaml](../../deploy/hindsight/compose.yaml) to upstream 1.1.0 and its immutable manifest digest. A pin change must be tested deliberately; the setup never floats to latest. Upstream references: [installation](https://hindsight.vectorize.io/developer/installation), [models](https://hindsight.vectorize.io/developer/models), [v1.1.0 release](https://github.com/vectorize-io/hindsight/releases/tag/v1.1.0).

Run all commands from the repository root. If `DOCKER_HOST` points at a different daemon, select the intended context explicitly, for example `docker --context desktop-linux compose ...` on Docker Desktop. Do not change another project's containers or daemon settings to make this setup work.

## Container-to-proxy networking

`localhost` inside Hindsight is the container, not the host.

| Existing proxy location | Container URL and prerequisite |
|---|---|
| Docker Desktop host | `http://host.docker.internal:4000/v1`, if that proxy listener is reachable from Docker |
| Linux host | The same host name maps to host-gateway in Compose. The proxy must listen on a bridge-reachable host address; a listener bound only to 127.0.0.1 is not automatically reachable through the gateway. |
| Another Docker container | Use a reachable published host address, or a local Compose override connecting Hindsight to the proxy's existing network and use its service name. Do not create a new proxy here. |
| Existing remote/private proxy | Its permitted HTTPS OpenAI-compatible API URL, reachable from the container |

Keep Hindsight's API mapping on 127.0.0.1. Changing proxy reachability is separate from exposing Hindsight to a network. A shared-network override must retain the loopback API mapping and local providers. A custom API prefix is allowed; include the proxy's `/v1` prefix once, without `/chat/completions`.

## Supply deployment configuration

Hindsight uses `HINDSIGHT_API_*`; application `ENGINEERING_MEMORY_*` values do not automatically configure another process. Set these in the shell before Compose starts. Do not put a real credential in tracked files or command literals. Resolved Compose/inspect output contains container environment values, so do not publish it; use `config --quiet` for validation.

The provider is `openai`, meaning compatible HTTP through the proxy. Hindsight's LLM provider named `litellm` uses SDK provider dispatch and is not needed here. `HINDSIGHT_API_LLM_MODEL` is your existing proxy alias, not a hardcoded model or a new application setting. Change the backend behind the alias in the proxy.

PowerShell:

```powershell
$env:HINDSIGHT_API_LLM_BASE_URL = 'http://host.docker.internal:4000/v1'
$env:HINDSIGHT_API_LLM_MODEL = Read-Host 'Existing proxy model alias'
$proxySecret = Read-Host 'Proxy key' -AsSecureString
$env:HINDSIGHT_API_LLM_API_KEY = [System.Net.NetworkCredential]::new('', $proxySecret).Password
```

POSIX shell:

```bash
export HINDSIGHT_API_LLM_BASE_URL='http://host.docker.internal:4000/v1'
read -r -p 'Existing proxy model alias: ' HINDSIGHT_API_LLM_MODEL
export HINDSIGHT_API_LLM_MODEL
read -r -s -p 'Proxy key: ' HINDSIGHT_API_LLM_API_KEY
printf '\n'
export HINDSIGHT_API_LLM_API_KEY
```

This profile requires a nonempty client key so a missing key fails before startup. Only when your proxy intentionally accepts unauthenticated calls, set `HINDSIGHT_API_LLM_API_KEY` to the explicitly nonsecret value `keyless-proxy-placeholder`. It is not a provider credential. Never replace a missing proxy route/key with direct upstream access.

Optional host port: `$env:HINDSIGHT_DEV_PORT = '18888'` in PowerShell, or `export HINDSIGHT_DEV_PORT=18888` in a POSIX shell. The bind address remains loopback.

## Start and wait for readiness

```text
docker compose -f deploy/hindsight/compose.yaml config --quiet
docker compose -f deploy/hindsight/compose.yaml pull
docker compose -f deploy/hindsight/compose.yaml up -d --wait --wait-timeout 300
docker compose -f deploy/hindsight/compose.yaml ps
```

`config --quiet` rejects missing proxy URL, alias or key without dumping their values. Pull is preparation and may be slow. The five-minute startup bound waits for the container health check against `/health/ready`, which checks database readiness. If first-run model preparation exceeds that bound, inspect local readiness/resources and retry the wait with an explicit larger limit; do not assume an unhealthy service can extract.

The full image uses local embedding/reranker providers explicitly. One GiB shared memory and a dedicated named volume at `/home/hindsight/.pg0` support the upstream embedded database. The volume belongs to this Compose project, `engineering-memory-hindsight-dev`; it is distinct from application raw archives and SQLite import state. No production database is mounted.

Startup/health alone proves neither extraction nor proxy routing. Do not enable LLM payload/debug dumps for troubleshooting: the profile disables 4xx dumps and uses warning-level logging. Safe checks include container health, resource availability, route host/port, and proxy status metadata. Do not paste environment-bearing Docker output or backend error bodies into issues.

## Configure the host-side smoke connection

Use the existing application settings boundary. The smoke loads it once, but contacts only the engine. The existing required LLM URL must still be set; it may differ from the container-side proxy URL.

PowerShell:

```powershell
$env:ENGINEERING_MEMORY_HINDSIGHT__BASE_URL = 'http://127.0.0.1:8888'
$env:ENGINEERING_MEMORY_LLM__BASE_URL = 'http://127.0.0.1:4000/v1'
```

POSIX shell:

```bash
export ENGINEERING_MEMORY_HINDSIGHT__BASE_URL='http://127.0.0.1:8888'
export ENGINEERING_MEMORY_LLM__BASE_URL='http://127.0.0.1:4000/v1'
```

Adjust the port and proxy host address for your setup. Default local Hindsight is unauthenticated: leave `ENGINEERING_MEMORY_HINDSIGHT__TOKEN` unset. If deliberately testing a separately secured instance, set its dedicated engine bearer token externally. It is never the LiteLLM proxy key. URL credentials, query parameters and fragments are rejected by smoke. HTTP environment proxies and redirects are disabled for engine requests.

## Write and recall a synthetic fact

```text
uv run python -m engineering_memory.memory.hindsight.smoke
```

This explicitly invoked command spends extraction calls on one generated synthetic fact. It accepts no history file, arbitrary content or bank target. Every run generates `engineering-memory-smoke-<UUID>`, writes one synthetic document with a fixture timestamp, recalls a codename unique to that run and deletes only that bank. It does not touch `engineering-global`, the raw archive or import state. Two invocations must report different bank IDs.

Output is JSON: generated run/bank identity, UTC window, whether data was kept, HTTP smoke outcome, and `proxy_observation` explicitly marked unverified. Exit zero means completed retain, expected recalled fact, and successful cleanup (or intentionally kept data). Any stage failure exits nonzero with safe diagnostics. A 2xx accepted/pending write alone never counts as completion. No retain request is automatically retried.

`--timeout 180` bounds the entire run with a monotonic deadline, including a reserved cleanup budget of up to five seconds. `--keep-scratch` intentionally leaves this run's bank for inspection. A deadline or cleanup failure reports the generated identity for later cleanup; it never broadens the deletion target. Do not pass private history to this infrastructure probe.

## Prove the proxy route separately

Use an isolated smoke window and the configured alias; a dedicated proxy key identity can help correlation if the proxy supports one. From existing proxy observability, record a successful extraction request's timestamp, request identifier, status and alias matching the smoke window. There may be multiple LLM requests. Do not enable request/response body logging or record keys, headers or private content.

Record both results: (1) HTTP retain/recall passed, (2) proxy observation confirmed, or explicitly unverified. Engine success does not establish which route handled extraction. If proxy logs/metrics are unavailable, the routing acceptance criterion remains unverified. This repository does not pretend to administer or query an arbitrary operator proxy.

## Restart persistence and cleanup

Run smoke with `--keep-scratch` and retain its generated bank ID. Stop normally, start again, and use the pinned API's `/docs` on the local API port to repeat recall on exactly that generated scratch bank; the synthetic codename must remain. Then use the bank-delete operation on that same generated bank. Never substitute `engineering-global` or an arbitrary bank identity.

```text
docker compose -f deploy/hindsight/compose.yaml down
docker compose -f deploy/hindsight/compose.yaml up -d --wait --wait-timeout 300
```

Normal down preserves the named volume. When deliberately discarding this development instance, `docker compose -f deploy/hindsight/compose.yaml down --volumes` deletes only this Compose project's data volume; it is destructive and is not part of startup, smoke or normal shutdown. Keep other projects' volumes and the application archive/import-state paths out of this procedure.

## Test connectivity and API handoff to #16

Ordinary `uv run pytest` remains offline. [Smoke unit tests](../../tests/unit/test_hindsight_smoke.py) use httpx MockTransport, not a live service. Compose configuration checks run without a daemon when the CLI/plugin is installed and skip when unavailable. Live testing is explicitly invoked by the operator.

Future engine contract tests use the host engine URL, optional engine token, and unique scratch banks. The default production bank remains `engineering-global`; provisioning and retain mission are separate #16 work. No consumer (Hermes, Claude Code or Codex) should connect directly to this engine as its memory provider.

The pinned v1.1.0 source/OpenAPI declares retain at `/v1/default/banks/{bank_id}/memories`, recall at `/memories/recall`, readiness at `/health/ready`, and scratch cleanup at `/v1/default/banks/{bank_id}`. Smoke checks required methods in the running `/openapi.json` before writing. It prefers synchronous retain and observes a returned queued operation through the bank's operations endpoint if necessary.

Architecture §9 currently records `/retain` and `/recall` spellings. This deployment feature records the discrepancy without silently rewriting the production contract. #16 must verify the running pinned contract, upsert/idempotency/provenance/tag semantics and production mission before the adapter relies on them. Static upstream inspection and offline mocks are not that live verification.

## Validation status

Implementation provides offline verification and reproducible commands. Live image startup, extraction, restart persistence and proxy-side observation were deliberately deferred by the operator during issue #15 implementation. See [verification record](../../specs/014-local-hindsight-deployment/verification.md) for actual commands and results; no live deployment success is claimed.

The staged full-product Compose workflow is documented in [full-product.md](full-product.md). Engine-only commands here remain supported.

## Provision the bank before importing

After service readiness, enable bank configuration writes on the engine with
`HINDSIGHT_API_ENABLE_BANK_CONFIG_API=true`. Set the existing application settings
(`ENGINEERING_MEMORY_HINDSIGHT__BASE_URL`, optional `ENGINEERING_MEMORY_HINDSIGHT__TOKEN`,
and required `ENGINEERING_MEMORY_LLM__BASE_URL`) in the environment, then run:

```text
uv run engineering-memory provision
```

The command applies the complete Architecture §12 mission to the configured bank
(default `engineering-global`) and reports success only after exact read-back.
It can be rerun after interruption or against an existing bank. It creates no
conversation memories and preserves unrelated configuration. It does not delete
a bank if verification fails.

To evolve the policy, update Architecture §12 and the packaged
`memory/hindsight/mission.txt` together, then rerun provision. This changes future
extraction only; existing memories require a separate archive replay.

Opt-in provisioning checks use unique disposable banks, never the configured
production bank:

```powershell
$env:ENGINEERING_MEMORY_LIVE_STORE = '1'
$env:ENGINEERING_MEMORY_LIVE_STORE_URL = 'http://127.0.0.1:8888'
uv run pytest tests/integration/test_bank_provisioning.py -v
```

For authenticated test instances, provide `ENGINEERING_MEMORY_LIVE_STORE_TOKEN` in
the environment. Live checks require the pinned service and enabled config writes.
