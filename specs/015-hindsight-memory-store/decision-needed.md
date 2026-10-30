# Decision required: retry-safe oversized document delivery

Status: proposed, awaiting human decision. No architecture amendment approved.

## Verified conflict

The pinned running Hindsight 1.1.0 accepts one async item and honors its operation
UUID. It rejects multiple items with the same document identity in an async
request (HTTP 400). Sync permits shared-document items but ignores operation_id.
Consequently the approved combination of one-request replace/append multipart
delivery and retry-cost idempotency cannot be implemented as planned.

## Proposed resolution

Revise ADR-006 and this feature's oversized delivery requirement to submit one
complete conversation as one async item, leaving internal extraction chunking
to the engine. Keep stable document identity, original time, provenance and
operation UUID semantics. Enforce an explicit maximum total request size and
reject larger input without truncation. Stop promising adapter-level bounded
multipart delivery. Verify large single-item retain/replacement against the pin
before claiming this option meets revised acceptance.

This preserves retry-cost deduplication and requires a contract/architecture
decision rather than silently weakening the approved issue acceptance.

## Alternatives

- Keep the existing contract and investigate a different verified engine version
  or upstream change supporting ordered async items under one operation. No
  suitable replacement version has been established by this experiment.
- Submit sequential async replace/append operations with distinct UUIDs. This
  changes ADR-006's one-request semantics and exposes partial delivery; it needs
  a separate recovery design and is not an implementation-only workaround.
- Use synchronous multipart: rejected as a default because ignored operation_id
  fails the promised extraction-cost retry guarantee.

Implementation remains gated pending the human decision. Approval of the first
option authorizes drafting the ADR-006/issue-spec amendments and corresponding
large-document verification; it does not constitute a claim that they pass.
