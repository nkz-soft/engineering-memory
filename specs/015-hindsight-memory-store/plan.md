# Implementation Plan: Hindsight Memory Store

Branch: 015-hindsight-memory-store. Issue #16. Amendment approved 2026-10-30.

## Summary and verified contract

Implement the synchronous MemoryStore protocol with the existing httpx stack.
One conversation is one asynchronous replace item; the engine performs internal
chunking. Poll a client UUID operation until completed, with bounded deadlines.
The approved ADR-006 amendment supersedes the earlier multipart proposal: pinned
1.1.0 rejects duplicate document identities in queued batches, while synchronous
retain ignores operation_id. Source and real-instance experiments confirm the
/memories, /memories/recall and /operations/{id} routes. Large single-item replay,
provenance, strict tags and replacement passed on the pinned running image.

## Technical context

Python 3.13, Pydantic v2, existing httpx, pytest and Ruff. No new dependency or
adapter-owned storage. Hindsight remains behind memory/interface. Ordinary tests
are offline; live opt-in uses generated synthetic scratch banks and cleanup.
Development services use the #55 product Compose with OpenRouter via the supplied
HTTP(S) proxy environment. Credentials stay in the ignored product .env.

## Constitution check

- I: archive remains source of truth; pipeline archives before calling this boundary.
- II: source-derived document identity, original conversation timestamp, versioned
  provenance and tags are preserved. Retry UUIDs survive uncertain in-process outcomes.
- III: observe failing transport and guard tests before implementation, then bind
  all MS-1–MS-11 contracts and verify the actual engine, including large input.
- IV: production engine types and endpoints remain within memory/hindsight;
  guard direct, relative and indirect production imports.
- V: caller supplies sanitized enriched input; no payload/credential logging,
  no redirects/environment proxying on local engine requests. OpenRouter provider
  calls use the separately configured proxy in LiteLLM.

No constitution principle or stack change. User approved the ADR-006 contract
amendment explicitly. Original source timestamps remain distinct from imported_at.

## Delivery sequence

1. Record live compatibility evidence and amend ADR-006/section 9 explicitly.
2. Write failing tests for mapping, malformed responses, safe errors and strict
   scope; implement deterministic ordered conversation serialization and decoding.
3. Submit one item with async=true, replace, stable document_id and a UUID.
   Return only after completed status. Bound HTTP and completion deadlines.
4. Keep pending (fingerprint, UUID) per document after uncertainty. Exact retries
   reuse it; changed payload or deliberate new delivery after success gets a new
   UUID. Bound pending entries to 128; cross-process coordination stays with #20.
5. Enforce total encoded request limit (default 8 MiB), reject oversized input
   explicitly without truncation. Preserve Unicode, ordered messages and tool context.
6. Use all_strict tags, positive local result-count limit and validated complete
   provenance. Preserve distinct facts from one document. Missing provenance fails.
7. Bind reusable boundary contracts to stateful wire fixtures and real scratch
   banks. Test long-document replacement, operation replay and source timestamps.
8. Enforce production import isolation and synthetic violations. Run pytest,
   Ruff lint/format, live contracts and an independent code review. Resolve findings.
9. Commit/push and open a template-compliant PR closing #16; move to in-review.

## Error policy and ownership

Timeouts/connections and HTTP 429/502/503/504 become unavailable. Other refusals,
malformed data and terminal extraction failures become rejected. Unknown operation
identity cannot prove success. Client is injected (caller-owned) or constructed
(adapter-owned, close/context manager). Public errors omit response bodies and URLs.

## Alternatives

Direct pipeline engine calls violate Principle IV. SDK adds an unnecessary stack
surface. Separate async appends expose partial updates and violate the approved
one-operation replacement semantics. Sync multipart loses operation deduplication.
Permanent content-derived UUIDs prevent force/A-to-B-to-A refresh. A pin change
was not established as necessary after large single-item validation succeeded.
