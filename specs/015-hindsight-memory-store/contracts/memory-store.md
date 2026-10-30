# Memory Store Contract

The public protocol remains memory/interface/store.py; reusable MS-1–MS-11 apply.

Retain accepts sanitized EnrichedConversation, serializes ordered conversation
context into one complete async replace item, and returns None only after
extraction completes. Identity derives from source/native id; time is original.
Versioned string metadata preserves complete provenance. Unicode is lossless.
The default complete encoded request cap is 8 MiB; larger requests are rejected
before I/O without truncation. The engine handles internal extraction chunking.

Exact retries after uncertain outcomes reuse the pending UUID within the adapter
lifecycle. Changed payload and deliberate delivery after confirmed success get
fresh UUIDs. Durable cross-process retry coordination is deferred to #20.

Recall returns tuple[RecallResult, ...], strict tag intersection, empty tuple for
no matches, positive limits on facts rather than documents, and validated complete
provenance. Distinct facts are never deduplicated solely by document identity.

HTTP timeouts/connections and 429/502/503/504 are unavailable. Other refusals,
malformed data and terminal extraction failures are rejected. Errors never expose
response bodies, credentials, URLs or conversation content. Missing operations
cannot establish success. All requests and completion polling have finite deadlines.

The user approved replacing the original multipart requirement on 2026-10-30.
The pinned real 1.1.0 engine rejects async shared-document multipart; sync ignores
operation_id. Large single-item replay/replacement, provenance and strict tags
passed a live synthetic experiment. Adapter-specific live contracts remain required.
