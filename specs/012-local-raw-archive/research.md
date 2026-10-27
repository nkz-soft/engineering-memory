# Research: Local Raw Archive

**Date**: 2026-10-26

Research was based on the checked-in boundary, source/parser, model serialization, test pipeline, and architecture. A read-only research agent independently inspected these integration points. No third-party service behavior or new dependency is assumed.

## R1 — Preserve the existing paired boundary

**Decision**: Keep `store(enriched, original)`, `load`, and `load_original`, and add lazy identity enumeration with an optional source filter.

**Rationale**: `src/engineering_memory/archive/interface.py` already requires both-or-neither, last write wins, and durable-before-return. `tests/contracts/archive.py` covers RA-1–RA-9, including all-field equality and reopening. Enumeration is the missing operation for replay.

**Alternatives considered**: Implementation-only listing would couple replay to disk layout; exporting every body at once would break conversation-at-a-time processing.

## R2 — One versioned envelope per identity

**Decision**: `v1/<sha256(document_id UTF-8)>.json` stores both forms, identity, and integrity metadata. Exact original bytes use strict base64. Write through a temporary sibling and publish with replacement.

**Rationale**: `OpaqueIdentifier` permits native colons and path-like strings. Hashing the complete identity avoids path interpretation. One publication unit prevents mixed pairs. Validate identity against its expected digest and envelope models on every read.

**Alternatives considered**: Raw identifiers in filenames are unsafe and nonportable. Two separately updated files break pairing. Generation directories and pointers complicate cleanup. SQLite is not needed for this file layout.

## R3 — Reuse original-record parsing

**Decision**: Put `ChatGPTArchiveSource` in `ingestion/chatgpt/archive_source.py`. It decodes each original JSON record and invokes `conversation.parse_record`.

**Rationale**: `ChatGPTExportSource._Reader._convert` already retains exact UTF-8 record slices from the scanner; these are standalone conversation objects. No export reconstruction is needed. Reusing original bytes allows parser and sanitizer corrections.

**Alternatives considered**: Using archived enriched conversations would repeat old processing decisions. Adding ChatGPT semantics to archive storage would violate its responsibility.

## R4 — Resumable iteration

**Decision**: Explicit iterator objects for replay and local listing where per-record errors must allow continuation. A root listing failure is terminal; an individual corrupt record is attributed and iteration remains usable.

**Rationale**: `ingestion/source.py` CS-5 requires the next conversation after a format error to remain reachable. Existing `ChatGPTExportSource` uses this pattern because generators close when exceptions escape.

**Alternatives considered**: A simple generator is insufficient for per-record continuation. Silently skipping corrupt records loses source-of-truth data without reporting it.

## R5 — Replay acceptance without expanding orchestration

**Decision**: Run `tests/integration/pipeline.py::Pipeline` using real source/parser, sanitizer and classifier, local archive, and fake memory/state. Delete the export and reopen the archive before replay with fresh state.

**Rationale**: The harness already orders sanitize → classify → enrich → archive → retain → record. Fresh state prevents unchanged-content skips from making replay a no-op. Change a redaction rule and assert current output to prove originals drive replay.

**Alternatives considered**: A live memory engine is unnecessary for archive behavior. Shipping #19's production importer is outside scope.

## R6 — Concurrent readers, durability, and privacy

**Decision**: One writer, multiple independent readers; replace complete records, sync file data and supported directory metadata before success, and exercise supported Windows/Linux local filesystems. Record the limits of platform power-loss guarantees. Never embed content or raw exception text in boundary diagnostics.

**Rationale**: Architecture ADR-008 requires readers during import; RA-9 requires a fresh instance to read durable data. Principles I/V require preserving originals locally while serving sanitized normalized content only. File operations stay inside the implementation module, preserving interface-only exports in `archive/__init__.py`.

**Alternatives considered**: Deferred/background writes would allow extracted memory to outrun the archive. Full multi-writer concurrency, encryption/key management, and network filesystems need separate requirements.

## Clarification Review

Zero questions required. Functional scope, identities, lifecycle, failure behavior, privacy, integration, completion criteria, and terminology are clear after recording assumptions in the spec. User interaction is an internal boundary rather than a UI. Performance is bounded by one conversation at a time; corpus-wide throughput targets await measurement. Platform durability details are a verification obligation, not an unresolved product choice.

## Platform references

Windows publication uses a private standard-library ctypes adapter for
[MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw)
with replace-existing and write-through flags. Original reads use
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
with read/write/delete sharing so independent readers do not deliberately block
replacement. Concurrent tests exposed transient access-denied/sharing failures;
a bounded retry handles those statuses and persistent failures still cross as
`ArchiveUnavailable`. These calls supplement file fsync; Windows directory fsync
is not claimed. POSIX syncs newly created directory entries and publication.
