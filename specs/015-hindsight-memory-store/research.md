# Research: Hindsight Memory Store

## R1 — Pinned contract before implementation

**Decision**: Verify v1.1.0 source/OpenAPI and running behavior before finalizing transport mapping. Feature 014 pins digest sha256:50311d02b4d5d2b7c5242bd336edf8735df8374eaad496a92f49c83b37d2aa06.
**Rationale**: Feature 014 research records /memories and /memories/recall, conflicting with architecture §9. Its live extraction/proxy checks were deferred, not proven by issue closure.
**Alternatives considered**: Blindly coding §9 paths or treating a closed deployment issue as semantic validation.
**Evidence**: ../014-local-hindsight-deployment/research.md, ../014-local-hindsight-deployment/verification.md, ../../docs/development/local-hindsight.md.

## R2 — Retry-safe completion

**Decision**: Plan UUID operation ids, async submission and bounded polling behind synchronous retain; verify pinned support first.
**Rationale**: Current official documentation says synchronous retain ignores operation_id. Request acceptance alone cannot mean success. Unknown outcomes retain the pending key; confirmed new deliveries use new keys so force remains possible.
**Alternatives considered**: Synchronous submission with an ignored key; a forever-stable content hash key; expanding the public protocol with engine vocabulary.
**Source**: https://hindsight.vectorize.io/developer/api/retain (Safe Retries). Moving documentation is research evidence, not proof of pinned semantics.

## R3 — Recall mapping and strict scoping

**Decision**: Use string metadata to carry full provenance; verify response fields and strict tag mode against the pin.
**Rationale**: Current recall documentation uses text, document_id and string metadata. Default tag matching can include untagged results; scoped queries need verified strict matching, likely all_strict.
**Alternatives considered**: Guessing missing provenance; default tag filtering; dropping multiple facts from one document.
**Source**: https://hindsight.vectorize.io/developer/api/recall.

## R4 — Multipart replacement

**Decision**: One request with first item replace and subsequent items append, all sharing document identity and provenance.
**Rationale**: ADR-006 explicitly defines safe replacement of an oversized grown conversation.
**Alternatives considered**: Separate independently replayed append calls or per-message documents.
**Evidence**: ARCHITECTURE.md §§7,9 and ADR-006.

## R5 — Verification surfaces

**Decision**: Reuse tests/contracts/store.py and add transport, graph and real-instance tests. Ordinary pytest stays offline; live fixtures use unique synthetic scratch banks.
**Rationale**: Existing MS-1–MS-11 cover boundary behavior without engine inspection methods. Retry extraction suppression needs operation evidence beyond fact counts.
**Alternatives considered**: Mock-only validation, production-bank mutation, exact fact-count assertions.

No unresolved product clarification is needed. External semantic uncertainties are explicit implementation experiments with fail/stop criteria, not assumptions of successful behavior. No live server validation was performed during planning.

## R6 — Pinned HTTP schema inspection (2026-10-30, T003)

Inspected upstream tag `v1.1.0`, resolved through the GitHub commits API to
`a5a619b5ca59c5c39e0f96be6f7a31fabd136bd5`. Source:
[hindsight_api/api/http.py](https://github.com/vectorize-io/hindsight/blob/a5a619b5ca59c5c39e0f96be6f7a31fabd136bd5/hindsight-api-slim/hindsight_api/api/http.py).
This is source evidence, not verification of the deployed image digest.

- Retain is `POST /v1/default/banks/{bank_id}/memories`. `RetainRequest`
  accepts `items`, `async` (default false), and an optional UUID `operation_id`.
  The key is ignored for synchronous retain. Async submission with a key requires
  every item to resolve to one strategy; mixed strategies return HTTP 400.
- Each `MemoryItem` carries content, timestamp, document identity, metadata and
  tags. Its `update_mode` accepts replace or append. Source describes append as
  concatenation followed by reprocessing; ordered multipart behavior and stale
  tail removal still require the running-instance experiment.
- `RetainResponse` contains success, bank_id, items_count, async, and optional
  operation_id/operation_ids. Async acceptance is not completed extraction.
- Poll `GET /v1/default/banks/{bank_id}/operations/{operation_id}`. The status
  schema enumerates pending, processing, completed, failed, cancelled and
  not_found, with optional completion time, error and progress. Completed records
  expire after the configured retention window; not_found cannot prove success.
- Recall is `POST /v1/default/banks/{bank_id}/memories/recall` with query, tags,
  tags_match and max_tokens. There is no result-count limit field in RecallRequest;
  the adapter must enforce the interface limit locally. all_strict specifies AND
  matching while excluding untagged facts; the default any includes untagged facts.
- RecallResponse contains results. Each RecallResult includes id/text and optional
  document_id, string-valued metadata, tags and temporal fields. Their presence
  in the schema does not establish provenance round-trip behavior on the engine.

The endpoint discrepancy is confirmed in source. Architecture remains unchanged
until T004 verifies the pin on a running instance, as required by T005.

## R7 — Live async multipart incompatibility (2026-10-30)

The running digest reports API version 1.1.0. Its async retain rejects a request
containing two items with the same document_id with HTTP 400 before extraction.
Inspection of `/app/api/hindsight_api/engine/memory_engine.py`, method
`submit_async_retain`, confirms this is deliberate: queued children run in
parallel without a per-document gate, so duplicate document identities are
rejected to prevent races. The synchronous path folds those items sequentially,
but does not use the client operation_id for retry deduplication.

The single-item async compatibility experiment passes, including completed
operation replay, original mentioned_at, metadata/tags, strict unrelated-tag
exclusion, and replacement removing stale facts. Thus provider connectivity is
no longer the implementation blocker. Required async multipart in ADR-006 and
the current plan remains unsupported. See decision-needed.md before changing
the normative contract or implementing a substitute.

## R8 — Approved resolution and adapter validation (2026-10-30)

The user explicitly approved R7's single-async-item proposal. ADR-006, section 9,
feature specification, plan, data model and contract now describe one complete
async replace item with engine extraction chunking and an explicit 8 MiB default
whole-request cap. A synthetic large document with beginning/end facts passed
operation replay, provenance, strict scope and replacement in 33.92 seconds.
All eleven reusable memory boundary contracts then passed against the real
adapter on synthetic scratch banks (284.14 seconds). This resolves R7's design
gate; no claim is made that async shared-document multipart became supported.
