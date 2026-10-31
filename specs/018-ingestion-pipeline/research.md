# Research: Ingestion pipeline

## R1 — Existing sources normalize

**Decision**: Use ConversationSource.read() and SourceConversation directly.
**Evidence**: `ingestion/source.py` returns a normalized Conversation and OriginalPayload; its iterator contract remains usable after SourceFormatError.
**Rationale**: Avoid a second parser or normalization pass and preserve the original bytes supplied by the source.
**Alternatives considered**: New normalization interface or a generator wrapper; neither is needed, and a generator raising an exception would stop permanently.

## R2 — Skip and state timing

**Decision**: Use ImportState.find and shared may_skip with the pre-sanitization hash, persist imported only after retain, never persist skipped.
**Evidence**: `ingestion/state.py` documents raw hash semantics and rejects stored skipped records; `sqlite_state.py` implements this boundary.
**Rationale**: Sanitized hashes would re-extract redacted conversations, while storing skips would destroy successful state.
**Alternatives considered**: Hash enriched payloads or skip on any record; both violate the existing contract.

## R3 — Enrichment and privacy

**Decision**: Build EnrichedConversation using sanitized content, existing Provenance and tag types; store original only through RawArchive.
**Evidence**: `normalization/provenance.py`, `normalization/tags.py`, `classification/classifier.py` and `archive/interface.py` define these values. Classification returns ProjectTag, including unknown.
**Rationale**: Stable identity and original time already belong to Conversation. Classifier does not return a repository; accept repository metadata explicitly when known.
**Alternatives considered**: Infer repository or semantic type with new classification logic; outside this feature.

## R4 — Partial failures and diagnostics

**Decision**: Per-item failure outcomes plus an optional terminal run error, safe stage categories and UTC times. Unknown parser identity remains absent; missing hashes do not become fabricated state records.
**Evidence**: SourceFormatError.subject is optional; ImportRecord requires source id, hash and document id. Architecture §18 requires continuation and failure reports, while constitution V forbids leaking contents.
**Rationale**: A report can express an unidentifiable malformed item without corrupting durable state. Arbitrary exception strings can contain secrets.
**Alternatives considered**: Persist invented ids or raw error text; invalid provenance and privacy behavior.

## R5 — Execution and retries

**Decision**: Sequential synchronous orchestration, adapter-owned retries, semantic result status for later CLI wiring.
**Evidence**: Existing boundary methods are synchronous; `memory/interface/store.py` hides transport details; architecture §18 specifies transient-only retries. The CLI is separately blocked by #19.
**Rationale**: Keeps the first composition small and deterministic, without changing adapter idempotency or adding parallel state writers.
**Alternatives considered**: Async pipeline, background queue and nested retries; unnecessary or out of MVP scope.

All technical questions were resolved against repository contracts. No external product behavior or new dependency is assumed.
