# Feature Specification: Hindsight Memory Store

Branch: 015-hindsight-memory-store. Issue #16. Approved for implementation.
The single-async-item amendment was approved by the user on 2026-10-30; see
ARCHITECTURE.md section 9 / ADR-006 and decision-needed.md for evidence.

## User stories and acceptance

1. Retain sanitized enriched history and recall facts through the existing
   engine-neutral boundary. Results preserve complete provenance, original time,
   stable source identity and strict project tags. Positive limits bound returned
   facts; empty matches return an empty tuple.
2. Retry uncertain delivery with the same operation UUID without queuing another
   extraction. Replace changed content at the same document identity. Deliberate
   deliveries after success, including A-to-B-to-A, get fresh operation identities.
3. Preserve large conversations as one async document, leaving extraction chunking
   to the engine. Recall beginning/end facts and replace without stale facts.
   Reject requests above an explicit total size limit; never truncate or silently
   split into independently applied append operations.

## Functional requirements

- FR-001: implement the unchanged MemoryStore protocol only inside memory/hindsight.
- FR-002: retain one conversation as one complete async item with stable document_id.
- FR-003: preserve original timestamp, versioned provenance, tags, ordered messages,
  roles and tool context; imported_at never substitutes for source time.
- FR-004: reuse UUID and exact payload after uncertainty within adapter lifecycle;
  changed payload and post-success deliveries start fresh operations.
- FR-005: preserve Unicode and full text. Default total request cap is 8 MiB;
  callers may configure the cap explicitly. Oversized requests fail before I/O.
- FR-006: strict tag intersection, validated provenance, positive limits and empty
  matches. Multiple distinct facts may belong to the same conversation.
- FR-007: safe permanent/transient boundary errors, finite HTTP/completion deadlines,
  no false success on acceptance, failure, cancelled or missing operation status.
- FR-008: graph guard rejects direct/relative/indirect production engine imports.
- FR-009: caller supplies sanitized EnrichedConversation after archiving; this
  boundary neither sanitizes nor changes pipeline/archive responsibilities.
- FR-010: verify pinned API and actual retain/recall including large replacement.

## Scope and limits

No public engine-specific API, new dependency, pipeline, provisioning command,
retry backoff or durable cross-process operation coordinator. Those belong to
existing follow-up issues. A single writer uses each store instance; memory
retains a bounded pending-operation map. Provider secrets and private exports
never enter fixtures, reports or commits. Live tests use disposable synthetic banks.
