# Research: Re-import idempotency

## Live infrastructure

**Decision**: Extend tests/integration/test_import_recall_e2e.py and deploy/hindsight/e2e.py.
**Rationale**: #23 supplies isolated bank provisioning, a real pipeline, pinned testcontainers engine, credential-free extraction, required-case checking and bounded cleanup. Its raw_fact helper returns a first match and must not be reused as a document-count assertion.
**Alternatives considered**: A second stack duplicates lifecycle code; a fake store cannot demonstrate engine upsert.

## Extraction evidence

**Decision**: Compare /stats call/error deltas from tests/integration/hindsight_contract/llm.py after completed imports; assert zero call delta only for intact-state unchanged replay.
**Rationale**: FixtureServer already counts calls under a lock and emits one world fact per supported synthetic marker. ARCHITECTURE section 17 assigns extraction avoidance to importer source-id/hash skip. Successful retains use fresh operation ids, and replay metadata can change, so recovery may legitimately extract again.
**Alternatives considered**: Billing assertions require external credentials; inferring extraction from importer counters leaves a blind spot.

## Recall and identity

**Decision**: Use a two-conversation corpus, broad plus per-member queries, sufficient supported recall limits and independent expected ids. Count distinct recalled document ids, and check one controlled fixture fact per id.
**Rationale**: Recall is ranked/budgeted and a single matching row proves existence only. Fact count is generally different from document count. The controlled small corpus and deterministic extraction allow stronger supplementary cardinality checks; required missing results fail.
**Alternatives considered**: Listing importer state is circular; arbitrary production-bank enumeration is outside this test's claim.

## Selective change and isolation

**Decision**: Record real MemoryStore retain identities with a transparent test-local forwarding observer. Each scenario starts from an independent baseline in a scratch bank; recovery deletes only disposed temporary SQLite state.
**Rationale**: Observed real submissions prove the recovery path was exercised and only the changed id was sent. Independent state prevents recovery from contaminating the edit case.
**Alternatives considered**: A mock replaces the boundary under test; a single long dependent scenario makes failures harder to localize.

## Clarification review

All functional, data, failure, privacy, dependency and completion requirements are clear. Nonfunctional bounds and service details reuse #23. No human question or governance decision is needed before the planned gate.
