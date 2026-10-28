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
