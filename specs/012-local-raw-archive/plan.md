# Implementation Plan: Local Raw Archive

**Branch**: `012-local-raw-archive` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: `/specs/012-local-raw-archive/spec.md`, issue #13.

## Summary

Implement `LocalRawArchive` behind the existing boundary, preserving exact originals and sanitized enriched conversations independently of Hindsight. Use a versioned JSON envelope per document, addressed by the SHA-256 of its complete document ID, with base64 original bytes. Publish a flushed temporary sibling through atomic replacement; readers see a complete old or new record. Extend the shared boundary with lazy identity enumeration and add a ChatGPT archive source that reparses original records through the existing parser. Prove full replay with the existing integration harness after deleting a synthetic export.

## Technical Context

**Language/Version**: Python 3.13.

**Primary Dependencies**: Existing Pydantic v2 models and pytest; standard-library pathlib, hashlib, json, base64, tempfile, and os. No new runtime dependencies.

**Storage**: Local directory configured through existing `Settings.archive_root`; no database or remote object storage.

**Testing**: pytest reusable contracts, focused filesystem and replay unit tests, integration pipeline acceptance, existing structure and privacy tests; Ruff.

**Target Platform**: Local Windows and Linux filesystems, including the Linux container; atomic-publication and durability tests must exercise supported filesystems.

**Project Type**: Python modular monolith with library boundaries and CLI; this feature introduces no command or consumer tool.

**Performance Goals**: Stream identities and read one record at a time. No corpus-wide materialization of bodies; no arbitrary latency SLA for an unmeasured local corpus.

**Constraints**: Exact bytes; complete paired publication; durable before return; opaque native IDs; no payload diagnostics; independent concurrent readers; one writer per root; no export-dependent replay.

**Scale/Scope**: Years of personal ChatGPT history. Memory proportional to one record plus parser state. In-memory fake may materialize keys; local enumeration uses filesystem iteration. No network filesystem or distributed-write guarantee.

## Constitution Check

*Pre-research gate: PASS. Post-design gate: PASS. No deviations.*

| Principle | Compliance and evidence planned |
|---|---|
| I — Raw archive source of truth | Preserve both forms together; durable reopen contract; delete export before original-based replay; archive precedes retain in the harness. |
| II — Provenance and stable identity | Use existing `document_id`, full enriched-model serialization, original timestamps and content hashing; replacement by identity without duplicates. Import-state/extraction policy is unchanged. |
| III — Test first | In implementation, write and observe failing contract, persistence, failure-injection, and replay tests before their corresponding code. This planning commit introduces no implementation. |
| IV — Replaceable boundaries | Keep existing methods; add enumeration to `RawArchive` and both implementations. Keep filesystem imports out of interface exports; ChatGPT parsing stays in ingestion, not storage. |
| V — Secrets never reach memory | Caller stores sanitized enriched content and unsanitized local originals. Replay reapplies sanitization before retention. Safe boundary diagnostics; synthetic fixtures only. No consumer original-read path. |

Stack: unchanged (ADR-004). Scope: architecture §§14, 21–22, Phase 1 item 6. Governance: issue selects none; no constitutional amendment, new source, or ADR required. Update architecture §§14 and 20 during implementation to point to the settled layout and remove its open-layout item. Concurrent readers required by ADR-008 are included from the start.

## Project Structure

### Documentation (this feature)

```text
specs/012-local-raw-archive/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/raw-archive.md
```

`tasks.md` is generated only after human approval.

### Source Code (repository root)

```text
src/engineering_memory/archive/
├── __init__.py                 # interface-only exports remain
├── interface.py                # add iter_document_ids
└── local.py                    # LocalRawArchive and private envelope/IO helpers
src/engineering_memory/ingestion/chatgpt/
└── archive_source.py           # ChatGPTArchiveSource, reparses originals

tests/contracts/archive.py     # extend reusable contract
tests/contracts/test_local_archive_passes_the_contract.py
tests/fakes/archive.py          # same enumeration semantics
tests/unit/test_local_archive.py
tests/unit/test_archive_replay_source.py
tests/integration/test_archive_replay.py
ARCHITECTURE.md                # settle §§14, 20 layout detail
```

**Structure Decision**: Put concrete filesystem behavior in `archive/local.py`; package initialization must continue to export only the boundary. Use source-specific replay in `ingestion/chatgpt`, reusing `parse_record`, not duplicating parser behavior or teaching storage ChatGPT formats.

## Design and Implementation Sequence

1. Extend reusable contract with enumeration: empty, unique, replacement, source filter, stable membership without writes, and declared iteration failures. Update the in-memory fake. Ensure broken implementations fail these tests.
2. Write local contract adapter and round-trip tests first. Implement version-1 envelope, digest addressing, model validation, and lookup without changing existing store/load signatures.
3. Add publication failure injection, reopening, concurrent-reader replacement, corruption, unsupported-version, binary, hostile-ID, and redaction-canary tests before implementing corresponding handling. Avoid any logger or error text that embeds payloads.
4. Write replay source tests first; implement a resumable iterator using `iter_document_ids(source=Source.CHATGPT)` and existing `parse_record`. Validate reconstructed identity and media type. Map parse failures safely and keep subsequent documents available.
5. Write export-deletion integration acceptance first, using real parser, sanitizer and classifier with fake memory and fresh import state. A changed redaction rule must change replay output from the original, proving it was not loaded from the old normalized form. Keep production orchestration for #19.
6. Document final layout in architecture; verify the focused suites, full regression suite, format/lint checks, and boundary import constraints. Review the finished branch before opening the PR from the repository template.

### Publication and durability

Create the archive root on first store, not construction or read. Use one temporary file in the destination directory, serialize and validate the complete record, flush and sync its bytes, then replace the destination. On platforms supporting directory synchronization, sync the directory entry before returning. Handle newly created directory durability as part of publication. Implementation must verify platform-specific behavior rather than silently skipping a failed supported sync. Windows requires its own documented and tested supported-filesystem durability path. The acceptance guarantee is complete records surviving process exit/reopening; do not claim universal sudden-power-loss resilience on arbitrary filesystems.

An error before publication preserves the old record. A sync error after publication reports `ArchiveUnavailable`; the new complete record may already exist, so retry is safe and tests must not demand rollback after publication. Clean temporary siblings on ordinary failure; ignore crash leftovers during enumeration. Concurrent `load` calls each observe complete envelopes; separate calls to load each form do not promise a shared revision if a writer commits between calls.

### Error and privacy policy

Missing committed path: `ArchiveDocumentNotFound`. Unreadable/unwritable filesystem, full disk, or failed supported synchronization: `ArchiveUnavailable`. Invalid envelope, unsupported format, inconsistent identity/hash, invalid base64, or model rejection: `ArchiveRejected`. Use fixed safe messages and document subjects; do not interpolate raw exceptions or validation inputs. Do not log originals, normalized contents, or private filesystem paths. Follow existing chained-cause diagnostic handling; consumers must not render raw causes.

Enumeration yields unique document IDs from validated committed records, source-filtered when requested. It must not parse all bodies merely to collect identities: read one envelope at a time. A malformed entry raises a declared error, never vanishes silently. Use a resumable iterator for per-record enumeration errors so replay can report that record and continue; terminal directory-listing failures stop that enumeration with a declared availability error.

## Alternatives Considered

- Normalized-only storage: rejected in the issue because parser and redaction changes require originals.
- Native IDs as path components: rejected for traversal, filesystem portability, and collisions.
- Two independently replaced files: rejected because readers can observe mixed forms. Immutable generations plus a manifest would work but introduce garbage collection and more publication state than a single envelope needs.
- SQLite archive: unnecessary backend and binary database format for this local-file feature; import state remains SQLite behind its own boundary.
- Replay from saved normalized form: cannot correct parser mistakes or restore content for changed redaction rules.
- Shipping the production importer/CLI now: exceeds #13 and duplicates #19; use the existing full pipeline test harness as the acceptance driver.

## Complexity Tracking

No constitutional violations. Base64 costs storage space and envelope reads decode one conversation, accepted for simple atomic pairing. Enumeration reads records rather than maintaining a second index; an index is deferred until measurement justifies it.

## Review Gate

Specification, checklist and design artifacts are committed and pushed before implementation. Record assumptions, open items and commit on issue #13. Stop for explicit human approval; no tasks, implementation, or PR at this gate. Open items: none blocking; platform durability is an implementation verification obligation stated above.
