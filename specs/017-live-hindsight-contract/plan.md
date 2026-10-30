# Implementation Plan: Live Hindsight Contract

**Branch**: `017-live-hindsight-contract` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)
**Input**: Issue #18; feature specification in this directory.

## Summary

Promote existing opt-in compatibility experiments into a dedicated live CI contract suite and extend them to all §6/9/10 invariants. Use the actual pinned Hindsight service and a deterministic, schema-aware OpenAI-compatible extraction fixture for credential-free CI. The fixture is an LLM dependency substitute only, never a substitute for retain, persistence, queueing or recall.

## Technical Context

**Language/Version**: Python 3.13, uv.
**Primary Dependencies**: existing pytest/httpx; repository Docker Compose engine definition. Standard-library fixture service; no new runtime dependency.
**Storage**: live engine's disposable PostgreSQL volume and unique scratch banks; no raw history.
**Testing**: pytest offline harness tests, live HTTP contract scenarios and CI workflow structure checks.
**Target Platform**: Linux Docker CI; local Docker with host-side pytest, including PowerShell.
**Project Type**: internal verification of the existing modular monolith.
**Performance Goals**: bounded readiness and per-operation waits; dedicated CI job timeout of 25 minutes initially, tuned only from evidence.
**Constraints**: no secrets required in fork PRs; no production bank access; no engine mocks; no generic chronological ranking assumption.
**Scale/Scope**: five contract families, minimal synthetic facts, one pinned engine service.

## Constitution Check

Pre-research and post-design gates: PASS; no deviations.

1. Raw archive: synthetic direct-engine compatibility tests are not an importer and create no production history. No archive behavior changes.
2. Provenance and identity: source-native stable document identifiers and original timestamps are explicitly verified; replay must not duplicate extraction.
3. Test first: write failing harness/CI checks and mutation controls before supporting implementation; observe failures before making them green. Live assertions precede any adapter correction; contract drift is reported rather than relaxed.
4. Replaceable boundaries: engine-specific HTTP inspection stays in tests of the memory implementation; domain, ingestion and access do not gain Hindsight dependencies.
5. Secrets: synthetic fixtures only, local fixture endpoint, no paid credentials; logs identify scenario/status/section without request bodies or headers.

Additional constraints: uses pinned self-hosted service; one production bank policy unchanged because scratch banks are isolated test resources. No stack or governance amendment is needed.

## Project Structure

### Documentation

spec.md, plan.md, research.md, data-model.md, quickstart.md, contracts/live-suite.md and checklists/requirements.md. tasks.md is intentionally deferred until human approval.

### Source Code (planned)

- `tests/integration/test_hindsight_store.py`: preserve or split existing live scenarios into independently named contract tests.
- `tests/integration/conftest.py`: scoped live HTTP fixtures, bounded waits and cleanup.
- `tests/integration/hindsight_contract/`: synthetic extraction fixture and scenario expectations if separation improves clarity.
- `tests/unit/`: fixture protocol and assertion negative controls.
- `tests/structure/test_ci_workflow.py`: verify the live job is active and cannot silently skip.
- `deploy/hindsight/`: test-only Compose overlay reusing `service.yaml`, isolated volume and fixture service.
- `.github/workflows/ci.yml`: dedicated live-contract job, separate from fast offline checks.

**Structure Decision**: Extend the existing live test location and canonical engine deployment rather than add a second engine configuration or application interface.

## Design and Verification

1. Create scratch-bank fixtures with unique run prefix, explicit local opt-in, optional existing token support, and safe cleanup limited to generated banks. CI explicitly enables the suite; local offline tests continue skipping it.
2. Add a fail-closed extraction fixture matched to the pinned engine protocol. Inspect the actual engine requests/schema during implementation before committing response fixtures. Keep embeddings, reranker, queue and database real. Track extraction calls, and provide a synchronization barrier to replay an operation while it is pending. Unknown requests fail with sanitized diagnostics.
3. Use independent small fact sets. Default-mode test omits update_mode deliberately and checks document inventory plus stale/new fact identities. Preserve explicit-replace adapter coverage separately.
4. Replay the identical async payload and operation_id before and after completion. Assert identical operation identity/completion, unchanged document/fact inventory, and no increment in extraction count after replay. Verify the counter can detect a distinct new operation.
5. Encode an explicit tag truth table for engine mode names (including any/all and strict variants accepted by the pinned API). Include overlap, disjoint, exact tag sets and untagged records; test empty filters separately. Inspect pinned schema/source for naming; if §6 uses inaccurate shorthand, propose a documented correction rather than weaken assertions.
6. Retain original dates in reverse ingestion order. Assert per-item recall dates and temporally scoped selection using the pinned API's supported temporal controls. Do not assert relevance results are sorted chronologically. A missing historical selection capability is a contract finding requiring resolution, not a skipped scenario.
7. Assert recall 404 for a unique untouched bank, then verify the read has not created it. Never provision this scenario's bank first.
8. CI starts an isolated Compose project, waits for health, enables the full suite, asserts nonzero execution with zero skips, and always tears down volumes. Failure diagnostics stay synthetic and sanitized. Model downloads need bounded readiness and a cache where practical.
9. Validate offline pytest, Ruff lint/format, harness negative controls, two live runs, and the actual CI job. An engine regression blocks the job; it is not addressed by updating expected results blindly.

## Alternatives Considered

- Trust documentation and test only our adapter: rejected by the constitution's live-contract requirement.
- Existing opt-in tests alone: useful baseline, but no CI gate and incomplete match-mode/default/time coverage.
- Paid external model credentials in CI: excludes fork PRs and adds cost and nondeterminism.
- Mock Hindsight: cannot verify its actual persistence, async idempotency or filtering semantics.

## Risks and Limits

Fixture protocol may require multiple structured extraction responses; fail closed and validate each against real pinned-engine execution. Deterministic extraction does not measure LLM quality. Temporal retrieval and tag mode vocabulary require pinned-schema inspection during implementation. CI resource/model-download requirements must be measured before claiming a stable gate. These are technical validation tasks, not changes in product scope.

## Complexity Tracking

No constitution violations or new production abstractions.
