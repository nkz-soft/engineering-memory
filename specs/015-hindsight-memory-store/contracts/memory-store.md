# Memory Store Contract

Public interface remains src/engineering_memory/memory/interface/store.py. Existing MS-1–MS-11 in tests/contracts/store.py remain authoritative.

## Retain

Accept sanitized EnrichedConversation. Return None only after extraction completes. Preserve source-derived document identity, original start time and full provenance/tags. Retrying the same pending operation reuses its UUID; a confirmed new operation uses a new UUID. Changed content replaces old content. Multipart delivery uses one request, replace then append, without leaking fragments to callers.

The pending UUID is held within the adapter lifecycle. Cross-process operation persistence is an explicit orchestration follow-up for #20; content replacement remains safe across restart, but extraction-cost deduplication across restart is not claimed.

## Recall

Return tuple[RecallResult, ...]. Empty matches return (). Tags use strict intersection scoping. Positive limit bounds fact results, not unique documents. Preserve valid provenance; never invent missing source/project/import information. Do not deduplicate distinct facts based on common document identity.

## Errors and transport

Timeouts, connection failures and 429/502/503/504 become MemoryStoreUnavailable. Rejections, unauthorized calls, invalid inputs and malformed successful responses become MemoryStoreRejected. No public error exposes response body, credential, URL or conversation. Internal async polling has a finite deadline. No backoff/retry policy is added to the public interface.

## Pinned compatibility gate

Confirm actual routes, UUID operation behavior, completion polling, metadata propagation, timestamps, strict tags and ordered replace/append on v1.1.0. Reconcile §9 paths explicitly. If the pin cannot support the promised semantics, stop completion and document the needed contract/version/governance change rather than reducing guarantees.
