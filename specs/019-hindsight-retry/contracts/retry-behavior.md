# Memory adapter retry behavior contract

The public MemoryStore interface and wire payloads remain unchanged.

| Outcome | Automatic action | Terminal result |
|---|---|---|
| HTTP 429, 502, 503, 504 | Retry same request within bounds | MemoryStoreUnavailable |
| Request timeout while budget remains | Retry same request within bounds | MemoryStoreUnavailable |
| Causal connection reset | Retry same request within bounds | MemoryStoreUnavailable |
| Other transport failure | No retry | Existing safe unavailable error |
| Other non-success HTTP, including 400/401/403/500 | No retry | MemoryStoreRejected |
| Invalid successful response | No retry | MemoryStoreRejected |
| Extraction failed/cancelled | No retry | MemoryStoreRejected |
| Operation not_found | No retry | Existing MemoryStoreUnavailable |
| Expired absolute deadline | No sleep/request | MemoryStoreUnavailable |

The initial attempt is immediate. Four attempts means at most three retries. Delay before retry n is min(2**(n-1) + uniform(0,1), 8) seconds. Do not sleep if its end meets/exceeds deadline; check again before requests. Bound timeouts by remaining time and preserve owned transport cancellation. Polls and retries do not extend the logical operation deadline.

Retain attempts reuse byte-identical payloads, operation_id and document_id. Poll recovery does not resubmit retain. Recall preserves original query/tags/matching. Uncertain exhaustion preserves pending identity for a later unchanged call; changed content follows existing new-operation rules.

Emit fixed-name structured attempt and terminal events. Allowlisted fields: operation kind, request ordinal, attempt count, outcome, safe error category, HTTP status, elapsed milliseconds, prospective delay, bank and optional document/operation ID. Terminal outcome is success/rejected/exhausted/deadline. Record successful attempts explicitly. Never log URLs, queries, bodies, headers, credentials, raw exception text or traceback objects.
