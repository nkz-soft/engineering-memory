# Implementation Plan: Local Hindsight Deployment

**Branch**: `014-local-hindsight-deployment` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: `/specs/014-local-hindsight-deployment/spec.md`, issue #15.

## Summary

Add a Docker Compose development profile for the official full Hindsight image, persisted embedded database and local embeddings/reranking. Route extraction through the existing LiteLLM OpenAI-compatible endpoint using operator-supplied URL/key/alias. Document startup, host/container networking, readiness, persistence, shutdown and test connectivity. Add a small synthetic-only scratch-bank smoke command inside memory/hindsight. Successful HTTP smoke and metadata-only proxy observation are separate acceptance evidence. Do not provision engineering-global or implement #16's production contract suite.

## Technical Context

**Language/Version**: Python 3.13 for smoke/tests; Docker Compose v2 for deployment.

**Primary Dependencies**: Existing Typer, settings and pytest; add httpx under ADR-004's HTTP-client choice when implementing smoke, and update uv.lock and dependency guard. No upstream SDK, new settings framework, shell-language dependency or replacement database library.

**Storage**: Dedicated Compose named volume mounted at `/home/hindsight/.pg0`; upstream embedded PostgreSQL remains inside Hindsight. Application SQLite/raw archive are unaffected.

**Target image**: `ghcr.io/vectorize-io/hindsight:1.1.0@sha256:50311d02b4d5d2b7c5242bd336edf8735df8374eaad496a92f49c83b37d2aa06`, observed in the official registry on 2026-10-27. Verify manifest/platform support during implementation. Version changes require an explicit tested pin update, never floating latest.

**Testing**: Offline HTTP simulation through httpx MockTransport and pytest; Compose rendering/validation without launching services; explicit live scratch-bank smoke and proxy observation after approval. The ordinary suite must not require Docker.

**Target Platform**: Linux Docker Engine and Windows/macOS Docker Desktop with Linux containers. Use PowerShell and POSIX examples in the guide.

**Project Type**: Development deployment plus narrowly scoped operational probe, within the existing modular monolith layout.

**Performance Goals**: Bounded readiness and smoke, not a throughput claim. Readiness default 300 seconds after image availability; smoke default 180 seconds overall, including calls/recall and cleanup budget. Timeouts configurable as positive command options. Image pull/model preparation are separately documented and may exceed readiness on a slow machine.

**Constraints**: Loopback API publishing only; no database publishing; no secrets committed or printed; no user-history input; unique scratch banks; alias owned by proxy; no direct provider credentials/fallback; opt-in live costs.

**Scale/Scope**: One local developer instance, one synthetic smoke fact per invocation; no production hardening, Kubernetes, proxy deployment, bank mission or ingestion work.

## Constitution Check

*Pre-research gate: PASS. Post-design gate: PASS. No principle or stack deviations.*

| Principle | Compliance and planned evidence |
|---|---|
| I — Raw archive source of truth | No importer changes or real history input. The scratch fact is a generated infrastructure probe, not imported history; production archive invariants remain. Documentation distinguishes engine volume from archive. |
| II — Provenance and stable identity | Smoke generates one run identity and uses its deterministic within-run document ID. No production ID/time changes; scratch timestamp is an explicitly synthetic fixed fixture time. Production provenance verification remains #16. |
| III — Test first | Write and observe failing smoke/configuration/security tests before implementation. Offline tests exercise bad statuses, malformed responses, deadline, cleanup boundaries and safe errors. Live acceptance cannot be substituted by mocks. |
| IV — Replaceable boundaries | HTTP routes/types live solely in memory/hindsight. Consume existing settings via load_settings; consumers still use the access surface. Administrative smoke is not a consumer write tool. |
| V — Secrets never reach memory | Only generated safe content is sent. Proxy/engine credentials supplied externally, kept distinct and omitted from errors. Local embeddings/reranking; self-hosted engine; loopback publishing. |

ADR-004 already selects Docker and httpx; engine-internal PostgreSQL is not a switch from the importer-state SQLite choice. ADR-002 permits scratch test banks through existing settings. ADR-003 production provisioning stays #16. Governance selects none. Current upstream routes differ from architecture §9's recorded spellings: record the discrepancy and verify the pinned OpenAPI; do not silently amend the production contract here. #16 must settle that recorded contract against the running instance before adapter work relies on it.

## Project Structure

### Documentation (this feature)

```text
specs/014-local-hindsight-deployment/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/development-setup.md
```

No tasks.md until the human approves this plan.

### Source Code and Deployment (repository root)

```text
deploy/hindsight/compose.yaml
 docs/development/local-hindsight.md
 src/engineering_memory/memory/hindsight/smoke.py
 tests/unit/test_hindsight_smoke.py
 tests/structure/test_hindsight_deployment.py
 README.md
 pyproject.toml
 uv.lock
```

**Structure Decision**: Compose and the guide are the startup script/document. Smoke is a runnable module under the engine implementation, using existing Typer for options and httpx for transport. Do not extend the production CLI or move upstream vocabulary into ingestion/access. Avoid adding deployment variables to application Settings merely to forward them to another service.

## Design and Implementation Sequence

1. Write failing deployment checks for immutable image identity, loopback mapping, private database, persistent volume and missing required proxy URL/alias. Compose uses explicit `HINDSIGHT_API_*` service settings; no populated environment file is committed. Render validation must suppress interpolated secret output (`config --quiet`, not dumping resolved config).
2. Add the full-image Compose service with 1 GiB shared memory, the pinned manifest, dedicated named volume, stable worker identity and explicit local embedding/reranker providers. Publish `127.0.0.1:8888:8888` by default; allow host-port override without widening bind address. Do not publish the bundled UI by default. No independent database container or host database port.
3. Document proxy networking separately for host and container. Docker Desktop may use host.docker.internal; Linux host-gateway mapping requires a proxy listener reachable from the Docker bridge. A localhost-only host listener is not automatically reachable through the gateway. Include an existing shared Docker-network alternative. Never solve reachability by silently exposing the engine broadly.
4. Set `HINDSIGHT_API_LLM_PROVIDER=openai`, explicit container-side base URL ending at the proxy's compatible API prefix, externally supplied alias in LLM_MODEL and proxy key (or a documented nonsecret placeholder if the client requires one for a keyless proxy). No physical model default and no fallback to a direct provider. Explain that application ENGINEERING_MEMORY_LLM__BASE_URL does not automatically configure the upstream container and may use a different host-side address.
5. Add httpx and failing smoke tests, then implement `uv run python -m engineering_memory.memory.hindsight.smoke`. Existing load_settings supplies the host engine URL and optional token. Pass only the dedicated engine token to engine HTTP calls; never the proxy credential. Use safe fixed stage/status diagnostics and trust_env=False to avoid unintended proxying of local calls. Do not render bodies, raw exception strings or secrets in URLs.
6. Generate `engineering-memory-smoke-<uuid>` and one synthetic fact such as a fictitious project's chosen codename. No input-file, arbitrary-content, production-bank or bank-id override. Use fixed fixture timestamp and document ID derived from run identity. Protect a cleanup target by validating that it equals the generated run bank and has the scratch prefix.
7. Verify readiness and pinned server OpenAPI before writing. Prefer synchronous retain (`async: false`), then recall the expected distinctive fact. Enforce one monotonic overall deadline and per-request remaining budgets. If the pinned API returns a queued operation, explicitly await completed or fail safely; never treat accepted/pending as retained. Avoid an automatic retain retry loop in this feature. Cleanup only the generated bank after success/failure, and make cleanup failure visible without exposing error bodies. An explicit keep-scratch option permits persistence/restart inspection.
8. Document routing verification as a separate operator check: isolate the smoke window, use the configured alias/dedicated key identity where supported, and record successful proxy request ID/time/status/alias. Do not turn on body logging or infer proxy usage from engine success. The smoke command reports write/read success only; the acceptance report includes whether proxy observation was confirmed.
9. Add host test-connection instructions using existing ENGINEERING_MEMORY_HINDSIGHT__BASE_URL, optional TOKEN and required existing LLM settings. Explain scratch banks, timeouts and how #16 reuses this instance. Link from README without claiming the pipeline is implemented. Document normal down versus explicit volume deletion and never remove unrelated volumes.

## Alternatives Considered

- Hosted Hindsight: rejected by issue #15, architecture §19.3 and Principle V.
- Existing one-off undocumented instance: cannot demonstrate clean-machine reproducibility.
- Slim image plus external embedding/reranking endpoints: introduces extra routes and prerequisites; full image keeps those local.
- Hindsight LLM provider named litellm: its SDK dispatch is unnecessary for an existing compatible proxy; use openai transport and a proxy alias.
- Fixed provider model in application Settings: contradicts architecture §19.4; the upstream container needs a route alias, not a hardcoded backend.
- Production bank smoke: risks real state and depends on #16's mission/provisioning. Use generated scratch banks only.
- Bash-only wrapper or new upstream Python SDK: Compose is cross-platform and httpx is the fixed HTTP client; a narrowly scoped module is enough.

## Verification Strategy

Before writing corresponding implementation, observe failing offline tests. Unit tests cover URL/token handling, retain/recall results, non-matching/empty result, malformed JSON, operation failure/pending, deadline, generated bank isolation, cleanup safety and secret-canary diagnostics. Deployment tests parse YAML and validate actual Compose behavior when Docker is present; ordinary tests remain usable without Docker.

After implementation run focused tests, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv lock --check`, and `git diff --check`. Then `docker compose -f deploy/hindsight/compose.yaml config --quiet` with external variables, startup/readiness, module smoke, metadata-only proxy observation, keep-scratch restart persistence and normal shutdown. Capture exact commands/results and image identity, with no credentials or payload logs. A live infrastructure prerequisite missing in the operator environment is reported as unverified acceptance, never replaced with a mocked success.

Baseline before implementation: `uv run pytest -q --tb=short -rs` on origin/main aee772b: 1571 passed, 4 existing skips in 50.94s. No service was started in planning.

## Complexity Tracking

No deviations. This feature intentionally validates infrastructure only. The §9/current-upstream route discrepancy is a documented handoff to #16, not a silent contract change. A live route incompatible with the architecture's required semantics must be reported before production use.
