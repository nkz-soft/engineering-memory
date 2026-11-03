# Research: Project mental models

**Date**: 2026-11-03. Repository inspection plus version-pinned upstream source research.
No running-instance or synthesis-quality acceptance is claimed in planning.

## R1 — Supported lifecycle

**Decision**: Use the pinned engine's native mental models behind a separate neutral adapter.
Repository `deploy/hindsight/service.yaml` pins 1.1.0 at digest
`sha256:50311d02b4d5d2b7c5242bd336edf8735df8374eaad496a92f49c83b37d2aa06`.

Relative to `/v1/default/banks/{bank_id}`, the pinned HTTP declarations provide:

| Action | Contract |
|---|---|
| Create | POST /mental-models with id/name/source_query/tags/max_tokens/trigger; returns mental_model_id/operation_id |
| Read | GET /mental-models/{id} |
| Definition update | PATCH /mental-models/{id} |
| Full refresh | POST /mental-models/{id}/refresh with mode full; returns queued operation_id |
| Completion | GET /operations/{operation_id} |

Create first persists empty content and schedules generation: POST success is not readiness.
Use existing bounded polling/error conventions, reconciling ambiguous writes before resubmission.

**Rationale**: Native persisted synthesis delivers standing context without a second RAG system.
**Alternatives**: Individual recall reconstruction; generation on every consumer read; arbitrary
model editing. None provides the required fixed, maintained standing picture as simply.

**Sources**: [Pinned HTTP source](https://github.com/vectorize-io/hindsight/blob/v1.1.0/hindsight-api-slim/hindsight_api/api/http.py),
[official lifecycle guide](https://hindsight.vectorize.io/developer/api/mental-models).
The guide tracks current releases; pinned source and live tests govern compatibility.

## R2 — Identity and strict project scope

**Decision**: Deterministic collision-resistant project/kind IDs, exactly one existing project
tag, explicit trigger.tags_match all_strict. Retrieve by stable ID and validate returned tags.

**Rationale**: Model tags also filter source memories. A kind tag would wrongly exclude history
without that tag. The listing endpoint supports any/all/exact rather than recall's all_strict;
listing is not the trusted lookup/scoping mechanism. Live tests must include untagged decoys.
**Alternatives**: Per-project banks violate ADR-002; random IDs duplicate definitions; slug-only
identity can collide; trusting request tags without response checks weakens boundary validation.

**Source**: Pinned HTTP source above; existing strict recall and provenance validation in
`memory/hindsight/store.py` and `serialization.py`.

## R3 — Freshness and explicit refresh

**Decision**: Explicit full refresh after successful imports; default 2048 tokens (upstream
permits 256–8192). Disable refresh_after_consolidation for managed definitions initially.
Expose successful refresh, nullable stale flag and newer refresh failure separately.

**Rationale**: The API provides last_refreshed_at, last_memory_seen_at, last_refresh_failed_at
and is_stale. Successful refresh time is wall-clock completion, not evidence time or a corpus
watermark. A failure preserves last-good content/time. Automatic consolidation refresh is
eventually consistent; it cannot make an import synchronously mean models are updated.
**Alternatives**: Automatic refresh per retain, scheduled workers and claiming all models
atomically current add scope/coupling. A failed maintenance run must not undo successful import state.

**Source**: Pinned HTTP source above. Preservation/freshness semantics remain live-test obligations.

## R4 — Evidence and replaceable boundaries

**Decision**: Separate ProjectModelReader/ProjectModelMaintainer capabilities; only the reader
crosses into access. Return multiple supporting archived conversations, never one fabricated
RecallResult provenance. Backend reflect_response contains based_on facts/observations; resolve
their source-document metadata inside the adapter, then verify project/archive identity.

**Rationale**: Existing MemoryStore has only retain/recall; access serves normalized archive
content, and consumers cannot write (constitution IV, ADR-008). Synthesis needs a distinct result
shape. The existing serialization format stores versioned provenance alongside deterministic IDs.
**Alternatives**: Leaking backend reflect objects, direct consumer engine configuration, or
re-retaining model content contradict the existing boundaries and archive grounding.

**Verification condition**: Exact fact/observation-to-document resolution and runtime response
shape must be established before acceptance. Unresolved/foreign provenance fails closed; do not
invent citations or silently substitute ordinary recall for the model. If the pinned engine cannot
provide required grounding, report a blocker and seek an explicit design/version decision.

**Sources**: Pinned HTTP source above, `memory/interface/store.py`, `access/service.py`,
`memory/hindsight/serialization.py`, constitution and architecture ADR-008.

## R5 — Acceptance and governance

**Decision**: Extend the live backend contract and add real-extractor semantic acceptance,
with held-out expected topics in synthetic fixtures. Record this contract extension as an ADR
despite the issue's unchecked contract-governance box. No new history source or stack change.

**Rationale**: §22 authorizes mental models in Phase 3; §21 only excludes them from MVP.
Constitution requires live tests of backend-dependent behavior. An LLM fixture proves lifecycle
but cannot prove that actual synthesis combines conversations or handles supersession correctly.
**Alternatives**: Mock-only verification, operation-success-only checks and a Phase 1 acceptance
claim would leave the issue's principal observable outcomes unproven.

**Sources**: ARCHITECTURE.md §§9,21,22; constitution I–V; existing isolated gates in deploy/hindsight.

## Research outcome

No unresolved product question; explicit refresh, fixed kinds and importer-side maintenance are
reviewable assumptions. API declarations support the design direction. Running-instance behavior
and synthesis quality are required Phase 2 proof, not assumptions promoted to fact.
