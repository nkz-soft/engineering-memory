# Raw Archive and Replay Contracts

## Existing operations

`RawArchive.store(enriched: EnrichedConversation, original: OriginalPayload) -> None`

- Both forms are one publication unit, durable before success.
- Identity and all enriched fields survive unchanged; exact original bytes and media type survive.
- Last successful write wins by document ID; no duplicate current entries.
- `ArchiveRejected` for invalid input/format, `ArchiveUnavailable` for failed storage operations.

`load(document_id: str) -> EnrichedConversation` and `load_original(document_id: str) -> OriginalPayload`

- Missing: `ArchiveDocumentNotFound` (permanent).
- Invalid stored record/version/integrity: `ArchiveRejected` (permanent).
- Unavailable storage: `ArchiveUnavailable` (retryable).
- Each call sees a complete committed envelope; two calls across a concurrent replacement may observe different revisions. No cross-call snapshot is promised by the existing API.

## Added enumeration

`iter_document_ids(*, source: Source | None = None) -> Iterator[str]`

- Return one full stable identity per current record; empty archive returns an empty iterator.
- With a source filter, return only that source; do not invent a new source.
- No order guarantee; repeatable membership when no writes occur.
- Read at most one conversation envelope at a time; no storage paths or implementation types cross the boundary.
- An absent root represents an empty archive on read and is created only on store.
- An individual corrupt record raises a declared error, advances the cursor and permits continuation. A root-listing failure raises a terminal declared error. Unpublished temporary files are ignored.
- A known corrupted record uses its ID as subject only when that identity is validated; otherwise use a safe record digest or no subject. Never fabricate an authoritative document identity from corrupt content.

Extend `tests/contracts/archive.py` beyond RA-1–RA-9 with empty/list/replacement/source-filter/repeatable-membership behavior. Shared fake/local tests cover declared failures as capabilities allow. Local-specific tests additionally verify durability, atomic replacement, corruption, filesystem safety, and concurrent readers. Keep the fake in `tests/fakes` and implementation imports out of `archive/__init__.py`.

## ChatGPT replay source

`ChatGPTArchiveSource(archive: RawArchive)` implements `ConversationSource`:

- `source = Source.CHATGPT`.
- Each `read()` starts fresh source-filtered enumeration.
- Each item loads exact original bytes, checks the supported JSON media type, decodes/parses one record with the existing `parse_record`, verifies the result's document ID, and yields `SourceConversation` with the original unchanged.
- It does not load the saved enriched form to construct replay conversations and does not read export paths.
- Use an explicit iterator, because per-document errors must not close iteration.
- Archive errors remain declared archive errors; parser errors become safe `SourceFormatError` values. Empty archive completes normally. No exception message may include original content, raw parser input, or untrusted library exception text.

A caller can swap local storage for an object-store implementation of `RawArchive` without changing this source or the pipeline. New history sources require their own specifications and decision records.

## Acceptance traceability

| Spec | Planned validation |
|---|---|
| FR-001–004 / SC-001,004 | Existing RA contracts plus all-field/binary reopening and publication failure injection. |
| FR-005–006 / SC-005 | Shared enumeration contracts; lazy local iteration and empty/source-filter tests. |
| FR-007–008 / SC-003 | Deleted-export full replay; changed processing rules; malformed record followed by valid record. |
| FR-009–010 | Boundary failure typing, diagnostic canaries, corrupt/future versions, identity/hash mismatch, hostile IDs and symlink rejection. |
| FR-011 / SC-002 | Reusable contract against fake/local; fresh local instance for RA-9. |
| FR-012–013 | Real sanitizer before retention in replay harness; no original content in output; archive failure prevents retain; no deletion operation. |
