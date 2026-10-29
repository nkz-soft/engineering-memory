# Implementation Plan: Full-product Compose

**Branch**: `015-full-product-compose` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)
**Input**: Issue #55, specification in this directory.

## Summary

Extend the existing Hindsight deployment into a shared development/live-E2E stack with a LiteLLM route, repository application image, explicit provision/import/status operations and read-only MCP stdio access. Keep offline configuration/lifecycle verification independent of credentials. Deliver infrastructure first if necessary; claim full-product acceptance only after upstream product capabilities land and live evidence exists.

## Technical Context

**Language/Version**: Python 3.13, uv locked dependencies; Compose YAML.
**Primary Dependencies**: Existing Dockerfile and Hindsight 1.1.0 digest pin; LiteLLM proxy image pinned during implementation, official MCP SDK through the existing access feature. Do not add an alternate application framework.
**Storage**: Local raw archive, SQLite state and Hindsight embedded database on project-scoped named volumes.
**Testing**: pytest unit/structure tests, Docker Compose validation and opt-in live product E2E; reuse upstream contract suites rather than recreating them.
**Target Platform**: Linux Docker Engine/Compose and Windows Docker Desktop with Linux containers.
**Project Type**: Local deployment and CLI orchestration for the modular monolith.
**Performance Goals**: Bounded operations, not throughput optimization. Defaults proposed: dependency startup 600s, extraction 600s, complete scenario 1800s, cleanup 60s; all positive configurable durations with one outer deadline preventing unbounded retries.
**Constraints**: No credentials in tracked files/reports, no conversation logging, no network MCP, no global resource pruning, no fixed E2E ports/container names.
**Scale/Scope**: One persistent development stack plus at least two independent concurrent E2E runs.

## Constitution Check

Pre-research and post-design gates both PASS; no deviations or new ADR required.

| Principle | Compliance in this design |
| --- | --- |
| I — Raw archive | Mount archive persistence separately from engine storage; E2E verifies original plus sanitized normalized archive through product behavior before/alongside retain. |
| II — Provenance/identity | Reuse importer identity, timestamp, tags and hashing; assert provenance and unchanged re-import, never generate substitute document ids in orchestration. |
| III — Test first | Each implementation change starts with an observed failing test; offline lifecycle/configuration and live product scenarios are specified below. No implementation is part of this planning commit. |
| IV — Boundaries | Provision/import use product CLI; retrieval uses product MCP SDK client over stdio. Only existing adapter knows engine protocol. No direct-engine recall substitute or new consumer endpoint. |
| V — Secrets | Environment/externally injected secrets, sanitized reports and normalized access only. Read-only local stdio access, self-hosted Hindsight and local archive remain intact. |

Keep Python/uv, SQLAlchemy SQLite, fixed shared development bank and the existing stack. Disposable banks isolate tests only. The one-shot runner is lifecycle orchestration, not a background worker or distributed ingestion feature. Scope matches architecture sections 21–22.

## Project Structure

### Documentation (this feature)

`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/lifecycle.md`, `quickstart.md`, `checklists/requirements.md`. Generate `tasks.md` only after human planning approval.

### Source Code (repository root)

- `deploy/hindsight/compose.yaml`: existing engine-only entry point, retained or refactored to reuse a shared engine definition.
- `deploy/product/compose.yaml`, `compose.dev.yaml`, `compose.e2e.yaml`, `litellm.yaml`, `.env.example`: proposed shared stack, environment differences and nonsecret model route.
- `src/engineering_memory/deployment/`: proposed Python lifecycle/preflight runner using subprocess argument arrays and bounded waits; no engine adapter implementation here.
- `Dockerfile`: retain installed application target; add an explicit test target if needed so pytest is absent from runtime.
- `tests/unit/`, `tests/structure/`: offline lifecycle failure/ownership/configuration tests.
- `tests/e2e/`: integrate scenario entry point owned by #23/#24 once available.
- `docs/development/full-product.md`, `docs/development/local-hindsight.md`: guide and engine-only compatibility pointer.

**Structure Decision**: Keep orchestration in the monolith and Compose deployment tree. Reuse pinned engine settings through a shared service definition/Compose merge with path resolution covered by tests; do not copy two independent Hindsight definitions. Final executable CLI spellings must match landed product commands.

## Delivery and Verification Design

1. Recheck main and upstream CLI/provision/MCP contracts. Record missing capabilities as blockers to the live scenario, never replace them with direct engine calls. Lock an available LiteLLM image digest and documented alias/provider mapping before introducing it.
2. Write failing offline tests for shared engine configuration, development volume persistence, E2E absence of host publications/fixed container names, environment validation, init dependency gating and secret-safe reports. Implement the base plus overrides and example. Verify `docker compose ... config --quiet` with nonsecret sentinel values; never print rendered configuration containing secrets.
3. Write failing runner tests using a fake subprocess boundary for concurrent identities, ownership validation, positive bounded deadlines, dependency/init failure, extraction failure, timeout, cancellation and cleanup errors. Implement cross-platform Python lifecycle runner and explicit one-shot operations. Reject development project names for test cleanup before launching any destructive command.
4. Integrate provisioning via #17 and CLI #21. Gate imports on successful mission/bank initialization; an engine health check alone is insufficient. Mount persistent archive/state directories writable by image UID 10001; verify first-use volume ownership. Avoid publishing app/proxy ports.
5. Integrate #23/#24 product E2E: synthetic import through CLI, real extraction completion, retrieval with official MCP client over an attached `compose run --rm -T` process and empty protocol stdout except MCP frames, archive/provenance checks and unchanged re-import. Read extraction status through product capability; missing lifecycle status is a prerequisite contract gap, not permission to couple orchestration to Hindsight endpoints.
6. Start each E2E invocation with a unique safe project token and bank; no host ports, no external volumes and no container_name. Inject project-specific paths and bank to every one-shot service. Cleanup in finally plus handled termination; retain recovery identifiers for hard kill where process cleanup cannot execute. Compose project-scoped down removes only owned resources; timeout/error is reported separately without masking scenario failure.
7. Document exact first-run/start/stop/rebuild/stdio/reset commands, external proxy variant and CI secret injection. Require explicit live flag; absent credentials/product prerequisites yield a visible skip before live mutation, while invalid supplied configuration or failure after a requested configured run yields failure. CI must report skipped live runs distinctly.
8. Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, Compose quiet validation and offline runner checks. With prerequisites/credentials, record exact live commands, concurrency and persistence results. Validate Windows and Linux independently; mark outstanding checks honestly.

## Alternatives Considered

- Continue engine-only setup plus manually managed proxy/application: reproduces the implicit machine dependency that caused #55.
- Mock-only E2E: suitable for lifecycle unit tests but proves neither extraction nor product retrieval.
- Independent Compose stacks: rejected because engine settings would drift.
- Production hosting, network MCP or web application: outside Phase 1 scope and would alter access/security constraints.
- Host-specific shell runner: rejected in favor of the existing Python runtime for Windows/Linux semantics.

## Complexity Tracking

No constitution violations. One deployment runner and shared Compose definitions are the minimum orchestration needed for owned cleanup and cross-platform deadlines. No new service architecture or persistence model.
