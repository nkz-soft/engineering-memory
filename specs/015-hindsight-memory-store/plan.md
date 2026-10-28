# Implementation Plan: Hindsight Memory Store

**Branch**: `015-hindsight-memory-store` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

## Summary

Implement the existing synchronous `MemoryStore` protocol in `memory/hindsight` using httpx. Preserve full conversation context, stable document identity, real timestamps, tags and provenance. Oversized documents use one request, first item replace and remaining items append (ADR-006). Internally submit asynchronous extraction and wait for completion if pinned verification confirms this is required for retry idempotency. The public method returns only after success.

## Technical Context

**Language/Version**: Python 3.13.
**Primary Dependencies**: Existing httpx, Pydantic v2, configuration and observability boundaries; no new runtime dependency.
**Storage**: Self-hosted Hindsight 1.1.0 pinned by feature 014; no adapter-owned database.
**Testing**: pytest reusable contracts, mock HTTP transport, import graph checks, explicitly enabled real-instance tests.
**Target Platform**: Local Python application on Windows/Linux with Docker engine deployment.
**Project Type**: Modular monolith and external HTTP service.
**Performance Goals**: Finite request and completion deadlines, bounded per-item payloads; no speculative throughput target.
**Constraints**: Shared engineering-global bank, sanitized inputs, no payload logging, unchanged engine-neutral protocol.
**Scale/Scope**: One conversation per operation; multiple ordered items in one request. Reject unsupported total sizes explicitly rather than silently truncating.

## Constitution Check

| Principle | Design and verification |
|---|---|
| I — Archive source of truth | Pipeline archives first; adapter receives enriched input and introduces no alternate archive. |
| II — Provenance/identity | Stable derived id, source start time, metadata/tags on every part; verify retries and round-trip on real engine. |
| III — Test first | Phase 2 observes failing tests before each implementation change; reusable contracts plus real retain/recall. |
| IV — Replaceable boundaries | Existing protocol unchanged; concrete types, HTTP and engine vocabulary confined to memory/hindsight. Import graph guard includes indirect imports. |
| V — Secrets | Sanitized inputs only; environment credentials, disabled redirects/environment proxies, safe errors and no content logging. |

Pre-design and post-design assessment: design fits all five principles. No deviations approved. Architecture endpoint discrepancy is an explicit implementation gate: reconcile documentation with verified pinned behavior; do not silently bypass §9. A semantic change requires its decision record and governance review.

## Project Structure

```text
specs/015-hindsight-memory-store/
  spec.md, plan.md, research.md, data-model.md, quickstart.md
  contracts/memory-store.md
  checklists/requirements.md
src/engineering_memory/memory/hindsight/
  store.py
  serialization.py
tests/
  contracts/test_hindsight_store_passes_the_contract.py
  unit/test_hindsight_store.py
  structure/test_memory_implementation_boundary.py
  integration/test_hindsight_store.py
```

**Structure Decision**: Extend existing adapter package; do not re-export implementation from the interface or parent package.

## Design and Verification Sequence

1. First write failing compatibility tests and inspect pinned OpenAPI/source plus a running instance. Feature 014 records /memories and /memories/recall, whereas §9 says /retain and /recall. Verify actual paths, async operation polling, strict tag matching, metadata availability and ordered replace/append semantics. Update §9 explicitly once proven. Stop implementation completion if required semantics cannot be demonstrated.
2. Inject synchronous httpx client, define ownership/close behavior, reuse settings, finite HTTP and overall completion deadlines. No redirects or environment proxies. Keep public calls synchronous while waiting for asynchronous extraction completion; never return success on mere acceptance.
3. Render messages in tuple order with role/time/tool context. Lossless deterministic UTF-8 splitting handles single oversized messages. Each part carries identical document id, original start time, string metadata and tags. First item replaces; subsequent items append in the same request.
4. Use UUID operation ids. Cache the pending operation key and exact payload fingerprint across uncertain outcomes; changed payload starts a new operation. Clear after confirmed success so intentional re-extraction and A→B→A refresh work. Do not derive permanent operation ids solely from content hashes. Durable cross-process retry coordination is deferred to #20, without adding an engine-specific public argument.
5. Preserve complete provenance in namespaced versioned string metadata, plus source time/document identity. Verify recall returns that metadata, or request included document metadata if the pinned API requires it. Rebuild validated `RecallResult` values; reject missing/invalid metadata. Use strict intersection tag semantics (verify all_strict), positive limits, and preserve distinct facts from the same document.
6. Timeouts/connections and 429/502/503/504 map to unavailable; rejected/unauthorized input, other refusals and malformed responses map to rejected. Keep messages safe and engine response bodies out. Retain bounded completion polling, but leave retry backoff policy to #20.
7. Bind tests/contracts/store.py MS-1–MS-11 to concrete adapter using a stateful transport fixture and to an explicitly enabled real scratch-bank fixture. Offline tests cover wire mapping, retry identity, Unicode/multipart, updated content, empty matches, strict filters, limits, malformed provenance, async failures/deadlines and safe errors.
8. Live tests use only synthetic facts and a uniquely named disposable bank, never destructive tests on engineering-global. Verify replace/upsert, retry extraction suppression, timestamps, metadata/tags and multipart replacement. Inspect operation identity/completion evidence rather than inferring extraction suppression solely from fact counts.
9. Enforce production import isolation with graph checks and synthetic violations. Existing architecture prose/configuration/deployment references are not forbidden engine dependencies; avoid naive text bans that reject established documentation.
10. Run uv run pytest, uv run ruff check ., uv run ruff format --check ., and explicit pinned-instance integration validation. Record commands/output and missing prerequisites honestly. Request code review before opening the template-compliant PR and changing labels.

## Alternatives Considered

- Pipeline HTTP calls rejected by Principle IV and ADR-001.
- SDK rejected in favor of existing httpx stack and narrow mapping.
- Per-message documents rejected by §7; separate append requests rejected by ADR-006.
- Synchronous wire extraction rejected if operation_id is ignored; bounded async completion preserves the synchronous public contract.
- Permanent content-derived operation keys rejected because force and A→B→A need new operations.
- Public engine operation-id parameters rejected to preserve the existing interface.

## Complexity Tracking

No proposed constitution deviation. Pending key storage is in-memory and bounded by the single-writer lifecycle; it is not durable import state. External contract verification is mandatory before claiming implementation completion.
