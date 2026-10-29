# Full-product development and E2E orchestration

This is the infrastructure increment for #55. It can start the pinned Hindsight
engine and a pinned LiteLLM proxy without an existing proxy container. Product
initialization, import/status, MCP and real E2E remain **blocked** on #16, #17,
#19, #21, #23 and #24. `start` fails explicitly; `e2e` reports `SKIPPED` with
exit 77. Neither dependency health nor these offline tests claim a live product
pass. The PR remains draft until the pending tasks in
[`tasks.md`](../../specs/015-full-product-compose/tasks.md) are completed.

## Configuration and dependency startup

Requires Python 3.13/uv, Docker with Linux containers and Compose 2.24.4 or newer
(the overlays use `!override`). Run commands from the repository root on Windows
PowerShell or Linux. `uv sync --locked` installs the environment. Copy
`deploy/product/.env.example` to `deploy/product/.env` and supply:

| Variable | Meaning |
| --- | --- |
| `PRODUCT_PROXY_KEY` | Operator-generated nonempty internal proxy master key; use a sufficiently long random value. In external mode, the existing proxy key or explicit nonsecret placeholder for a keyless proxy. |
| `PRODUCT_PROVIDER_MODEL` | LiteLLM provider-qualified model that your account can use, such as `openai/<enabled-model>`. Required internally. |
| `PRODUCT_PROVIDER_API_BASE` | Container-reachable OpenAI-compatible model-provider URL. Required internally. |
| `PRODUCT_PROVIDER_API_KEY` | Provider credential. Required internally; supply outside version control. |
| `PRODUCT_MODEL_ALIAS` | Optional. Internal route is `engineering-extraction`; changing it is rejected. External mode uses the alias already configured on your proxy. |
| `PRODUCT_PROXY_URL` | External mode only: container-reachable proxy URL ending in `/v1`. |
| `PRODUCT_DEV_PORT` | Optional loopback Hindsight host port, default 8889. Internal-only proxy and application publish no ports. |

The fixed internal alias maps to your provider model in `litellm.yaml`. This
configuration supports OpenAI-compatible providers; other providers may need a
separately reviewed route configuration. On Linux and Windows, a model service
on the host can use `host.docker.internal`; bind it to an interface reachable
from Docker and configure host firewall permissions as appropriate. Container
`localhost` refers to the container itself. The environment file is ignored by
git and excluded from Docker build contexts at every depth. Do not paste keys
into tracked YAML, commands, reports or issues. Provider usage is real and may
incur charges; configure any spending limit at the provider.

```text
uv run python deploy/product/run.py config
uv run python deploy/product/run.py dependencies
```

`config` checks syntax quietly without a daemon or credentials; placeholder
values used for validation cannot prove real model routing. `dependencies`
validates required inputs and waits for bounded service readiness. It creates
only the infrastructure, with no bank initialization or extraction. Defaults:
startup 600 seconds, total E2E 1800 seconds and cleanup 60 seconds. Set
`--startup-timeout`, `--total-timeout`, `--cleanup-timeout` to positive finite
seconds. The total E2E budget includes provision and scenario execution;
cleanup has a separate budget so timeouts can still clean up.

An existing external proxy remains supported:

```text
uv run python deploy/product/run.py config --external
uv run python deploy/product/run.py dependencies --external
```

Supply `PRODUCT_PROXY_URL`, `PRODUCT_PROXY_KEY` and the optional model alias.
Internal provider inputs are not needed in external mode; LiteLLM is disabled
and Hindsight has no dependency on it. Use the same mode when stopping/resetting.
The engine-only workflow at [`local-hindsight.md`](local-hindsight.md) remains
available with its original environment-variable names and project.

## Application development and data lifecycle

The application uses the repository Dockerfile and installed package. After
editing source, rebuild the application:

```text
docker compose -p engineering-memory-product-dev -f deploy/product/compose.yaml --profile tools --profile internal build app
```

That direct build requires `PRODUCT_PROXY_KEY` in the shell for Compose
interpolation; alternatively pass `--env-file deploy/product/.env` before `-p`.
A source mount alone cannot update the noneditable package in the runtime image.
All application roles share one project-local image. The image runs as UID
10001; archive/state mount directories are created and owned by that user so
fresh named volumes inherit usable permissions.

Development uses the fixed `engineering-memory-product-dev` project and
`engineering-global` bank. Archive, SQLite state and engine database persist on
three project-scoped named volumes. Ordinary stop preserves them:

```text
uv run python deploy/product/run.py stop
```

The **destructive reset** removes those development volumes and their original
history, state and engine records. Export/back up needed data beforehand:

```text
uv run python deploy/product/run.py reset --destroy-development-data
```

Stop/reset work after credentials are removed or blanked. They operate on the
product development project only, not the separate engine-only project or E2E
projects. Switching proxy modes does not migrate data. Do not run concurrent
development stacks under the same fixed project name.

## Pending product commands and MCP lifecycle

`start` is the future one-command development entry point. It currently fails
before creating containers because product initialization is unavailable.
The `provision`, `import`, `status`, `mcp` and `e2e` service roles are fail-closed
integration points, **not working product commands**. Reserved CLI names must
be aligned with #17/#21/access contracts before `capabilities.json` becomes
ready. `provision` must set bank and retain mission idempotently; import/status
and scenario work must depend on its successful completion.

The MCP role has attached stdin, no pseudo-terminal and no network port. Once
the actual product command is bound, consumers launch it via Compose run with
`--rm -T` and the same persistent application volumes. Product protocol alone
must use stdout; lifecycle messages must go to stderr. Consumer exit must end
the MCP process and remove the one-shot container. This transport acceptance
remains pending; no Hindsight MCP endpoint is offered as a substitute.

## E2E and CI

```text
uv run python deploy/product/run.py e2e --live
```

Currently this returns 77 and an explicit prerequisite skip before contacting
Docker. Omitting `--live` also returns 77. Once product prerequisites land,
missing credentials produce the same skip; partially supplied or invalid
configuration fails. A configured live run failing model authorization,
readiness, initialization or extraction must fail, not skip. Keep the ready
flag false until actual product commands and assertions replace the reserved
roles and placeholder scenario.

The runner is prepared to allocate a unique `em-e2e-<uuid>` project and bank.
E2E publishes no host ports; archive, SQLite, engine volumes and networks are
project-local. It waits for dependencies, runs provision, then the real
scenario. The scenario from #23/#24 must await extraction within its deadline,
verify original/sanitized archives and original provenance, retrieve the fact
and conversation through **product MCP stdio**, and verify unchanged re-import
skips extraction and creates no duplicates. A direct engine smoke cannot
satisfy these requirements. The runner's outer deadline bounds the entire
scenario even if extraction polling fails to stop.

Cleanup runs after success, failure, timeout, Ctrl+C and handled SIGTERM. It
removes volumes and orphans only from the identity generated by that run; no
prune or development reset is used. Cleanup failure returns a failing status
and an exact recovery project id. SIGKILL, machine shutdown or power loss can
leave resources; use that exact id with the E2E files and `docker compose -p
<exact-id> ... down --volumes --remove-orphans` after checking Docker project
labels. Never guess a prefix or use wildcard deletion.

Offline CI already runs pytest, which covers effective configuration and
lifecycle faults without provider calls. Effective Compose tests require the
Docker CLI/Compose plugin but no daemon; they explicitly skip if unavailable.
For configured CI, inject the four internal-provider inputs as environment
secrets, install uv/Docker/Compose, then invoke the same live command. Treat
exit 77 as a separate skipped result, exit 0 as pass and any other code as
failure. Do not convert all nonzero results to skips. Do not publish environment
dumps, rendered Compose output, raw provider logs or conversation payloads.

## Troubleshooting and validation status

The runner reports a safe failing stage or missing variable name and suppresses
raw subprocess output. Container log storage is disabled to prevent provider
errors or application payloads entering Docker logs. To investigate, check
Docker availability (`docker info`), image availability, configured endpoint,
provider authorization, model alias and deadline settings. Hindsight health
proves engine readiness, not successful extraction; provider-routing errors may
only appear during actual extraction. Do not enable detailed request logging
with private history.

See [`validation.md`](../../specs/015-full-product-compose/validation.md) for
exact checks. Windows host offline checks and Docker Compose rendering are
exercised; provider-backed extraction, full product persistence/concurrency,
Windows live startup and Linux runtime validation are outstanding. There is no
claimed full-product live pass on either platform.
