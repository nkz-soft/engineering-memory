# Implementation Plan: Retry transient Hindsight failures

**Branch**: `019-hindsight-retry` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)
**Status**: Awaiting human planning approval. Input: issue #20.

## Summary

Add Tenacity inside the Hindsight adapter raw-request boundary, before domain-error translation. Cover retain submission, status polling and recall. Preserve serialized bytes and operation identity; enforce four attempts per request and the original logical operation deadline. Emit safe structured attempt and terminal outcomes.

## Technical Context

**Language/Version**: Python 3.13.
**Primary Dependencies**: Existing httpx and structlog; add Tenacity (already selected by ADR-004) and update uv.lock.
**Storage**: Existing in-process pending identity map; no schema changes.
**Testing**: pytest, httpx.MockTransport, controlled clock/sleep/randomness; existing store contracts and pipeline regressions.
**Target Platform**: Existing local application and Linux container.
**Project Type**: Modular monolith; synchronous memory interface with owned async HTTP transport.
**Performance Goals**: Immediate first attempt; exponential delays with additive jitter, capped at eight seconds.
**Constraints**: Four total attempts per request; retain's existing 240-second and recall's 30-second default deadlines include all retries. No real history or secrets in fixtures/logs.
**Scale/Scope**: Runtime retain, polling and recall; provisioning and smoke-probe retries excluded as recorded assumptions.

## Constitution Check

Evaluated before research and after design: PASS, no deviations.

| Principle | Compliance and verification |
|---|---|
| I. Raw archive | Adapter-only change preserves archive-before-retain and replay; run pipeline regressions. |
| II. Provenance and identity | Serialize once and reuse UUID; preserve timestamps, metadata, tags and pending state. Test uncertain exhaustion, changed payload and later caller retry. |
| III. Test-first | Phase 2 writes each test and observes failure before implementation; run contracts and pipeline regressions. No implementation in this phase. |
| IV. Replaceable boundaries | Retry machinery stays in memory/hindsight; public interface and pipeline remain unchanged; run structure tests. |
| V. Secrets | Allowlist log fields; canary tests exclude queries, content, URLs, headers, credentials, response bodies and exception text. Sanitization order stays unchanged. |

Tenacity implements the existing stack row without displacement; no ADR, bank, tag or constitution changes. Scope fits architecture sections 21–22.

## Project Structure

### Documentation (this feature)

`specs/019-hindsight-retry/`: spec.md, plan.md, research.md, data-model.md, quickstart.md, checklists/requirements.md and contracts/retry-behavior.md. tasks.md is deferred until approval.

### Source Code (repository root)

- `src/engineering_memory/memory/hindsight/store.py`: integrate retries and events.
- `src/engineering_memory/memory/hindsight/retry.py`: private policy/classification helpers.
- `tests/unit/test_hindsight_retry.py`: planned policy, deadline and logging tests.
- `tests/unit/test_hindsight_store.py`: adapt existing identity/failure fixtures.
- Existing tests/contracts and tests/integration: regression verification.
- `pyproject.toml`, `uv.lock`: dependency and lock update.

**Structure Decision**: Extend the concrete adapter with private helpers; no new orchestration or persistence layer.

## Design and Implementation Sequence

1. Write failing classification and recovery tests. Add validated Tenacity policy: four total attempts, initial delay one second, cap eight seconds, jitter up to one second. Reject invalid/non-finite policy values before I/O.
2. Separate one raw request from decoding and error translation. Retry exactly 429/502/503/504, httpx.TimeoutException while time remains, and transport errors causally containing ConnectionResetError/ECONNRESET. Do not classify resets from message text. Other transport failures keep safe unavailable translation without retries.
3. Preserve absolute deadlines across submission, polls and retries. Check before requests and prospective sleeps; stop if sleep would meet/exceed deadline. Cap request timeout by remaining time and preserve owned-client cancellation. Map exhaustion to safe MemoryStoreUnavailable, never exposing Tenacity RetryError.
4. Reuse serialized submission bytes. Retry a failed poll without resubmitting retain. Preserve pending identity after uncertain exhaustion, definitive rejection cleanup, and prior uncertainty on rejected replay. Keep successful-response validation and extraction statuses outside retries.
5. Log explicit attempt outcomes and terminal outcomes using the existing observability logger and the allowlisted contract fields. Cover successful attempts, not only failure callbacks.
6. Update fixtures that expected an immediate transient failure to exhaust automatic retries before testing a later caller retry. Cover both sync injection and owned async transport; deterministic timing and privacy canaries. Run quickstart checks and review the finished branch before PR creation in Phase 2.

## Alternatives Considered

Retry-any-exception is explicitly rejected by issue #20 and section 18. Retrying MemoryStoreUnavailable loses classification and includes local deadline exhaustion/not_found. Wrapping retain resets too much work and may resubmit acknowledged extraction. Unbounded defaults and manual general loops are rejected in favor of bounded Tenacity. Administrative provisioning and synthetic smoke retries are deferred: they have separate boundaries and the probe includes diagnostic extraction and destructive cleanup.

## Complexity Tracking

No constitution violations or added architectural layers. No unresolved design questions; policy defaults and scope assumptions are reviewable at the planning gate.
