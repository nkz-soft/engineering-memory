# Proposed MCP tool contract

Transport: stdio; stdout is exclusively MCP protocol. Host starts/stops the process.
Tools listed: search_memory and get_conversation only. No mutation tools, resources
exposing files, network transport, retain, reflect or list_conversations.

## search_memory

Input: query (required nonblank string), tags (typed tag strings, default []), limit
(integer 1..100, default 10). Tags narrow conjunctively using existing recall semantics;
empty tags search the shared corpus. `project:unknown` is a valid explicit filter.
Output: results array, each containing content, document_id, provenance, started_at,
optional score. Empty results is success. Identity is source + ':' + source_id.
Each result must resolve to an archived normalized conversation for original time;
missing/corrupt archive is a tool failure, not a silently dropped fact.

## get_conversation

Input: document_id (required validated stable identity), offset (integer >=0, default
0), page_size (integer 1..100, default 50).
Output: document_id, provenance, started_at, messages, offset, next_offset.
Messages use archived order; next_offset equals offset + returned count when another
message exists, otherwise null. At/beyond the end returns [] and null. Unknown identity
is not-found; it is not an empty known conversation. Reject path-like invalid identities
before accessing storage. Original archive bytes are never read or returned.

## Errors and trust

Protocol input validation covers invalid arguments. Operational failures are tool errors
with stable safe codes: not_found, corrupt_record, unavailable, rejected. Return no
exception chain, URL, filesystem path, credentials, query content or history in errors.
Returned history is untrusted data, not instructions. Annotate both tools read-only.
Tool descriptions explain that consumers should search explicitly and cite provenance.
No conversation text is logged. Close backend clients at process shutdown.
