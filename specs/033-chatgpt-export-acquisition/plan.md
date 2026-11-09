# ChatGPT export acquisition implementation plan

**Branch** `033-chatgpt-export-acquisition`
**Date** 2026-11-09
**Spec** [Feature specification](spec.md)

## Summary

Add an upstream `ExportSource` for a manual ZIP and a configured local inbox. A one-shot command runs under the operator's existing scheduler. It stages and validates an immutable copy, publishes the original bytes, records acquisition, and then hands that copy to the existing incremental ChatGPT importer. It completes the acquisition only when the import reports success. [Research](research.md) records the alternatives.

## Technical Context

Python 3.13, Typer, SQLAlchemy 2 with SQLite, pytest and the standard library. Keep the SQLite store and archive on the same local host as the operator. Bound memory by streaming archive copies, CRC checks and conversation preflight. Apply finite limits to compressed size, expanded bytes and member count. Support the documented Windows and Linux deployments without a scheduler dependency or a long-running worker.

## Constitution Check

| Principle | Design and verification |
|---|---|
| I. Raw archive | Commit the exact ZIP to the raw archive before dispatch. Existing per-conversation originals, normalized forms and replay remain available. Prove retry after the inbox copy disappears. |
| II. Provenance and identity | Keep ZIP identity separate from conversation identity. Reuse source IDs, hashes, document IDs, tags, conversation timestamps and retain operations. Reuse successful conversation state on an interrupted import. |
| III. Test-first | Observe failing tests before each change. Run shared source contracts, archive and state failure tests, offline CLI flow, and the existing live integration gate for the import contract. |
| IV. Replaceable boundaries | Keep discovery, ZIP storage and acquisition state behind separate narrow interfaces. CLI composes them. The pipeline still receives a conversation source and retains its per-record error handling. ADR-007 records the added boundary. |
| V. Secrets | Stage privately under the archive root and log safe categories, never raw names, URLs or data. The current sanitizer still runs before retain. The watcher needs no mailbox or ChatGPT credentials. |

The checks pass at design level. No constitution or stack change is required. The signed-in download and the real export's timestamp evidence are operator validation steps.

## Project Structure

| Area | Planned change |
|---|---|
| `ingestion/acquisition*.py` | Define `ExportSource.discover()`, candidate/readiness values, acquisition outcomes and coordinator. Provide manual and local-inbox implementations. |
| `ingestion/chatgpt_preflight.py`, `ingestion/chatgpt/records.py` | Reuse supported ZIP member selection and streaming array scanner for strict preflight. Keep the ordinary parser's existing behavior. |
| `archive/export_blobs.py` | Define an export blob interface and local adapter. Reuse the filesystem durability helpers from `archive/local.py`. |
| `ingestion/acquisition_state.py`, `ingestion/sqlite_state.py` | Add the acquisition ledger and migration with independent interfaces for conversation and acquisition state. Preserve read-only v1 support. |
| `cli/__init__.py`, `runtime.py`, `results.py`, `settings.py` | Add one-shot acquisition and additive status output. Reuse import composition and isolate configuration in settings. |
| `ARCHITECTURE.md`, operator docs | Add boundary §8, archive and state notes in §§14 and 17, ADR-007, and a scheduler recipe. |
| `tests/` | Extend synthetic ZIP fixtures and cover contracts, malformed archives, storage/migration, recovery and the scheduled entry point. |

Paths in the table are under `src/engineering_memory/` unless they refer to documentation or tests.

## Design sequence

1. **Source and preflight.** Define discovery of explicit and scheduled candidates, with safe errors and a persisted inbox observation across invocations. Snapshot a stable regular file into private staging, rejecting redirects and rechecking identity, size and modification time after the copy. Stream the whole ZIP through integrity checks before offering it to ingestion. Pin a late corrupt member, invalid JSON tail, split-part ambiguity, input size limits and a candidate modified during copy in tests.
2. **Durable blob and ledger.** Publish the verified ZIP by digest, then record the acquisition as pending in SQLite. Stage and publish on the same filesystem. Check a pre-existing blob against its digest before reuse. Migrate writers from v1 to v2 transactionally, while status and preview still accept v1 without writes. Pin interrupted publication, migration rollback, existing v1 readers, and the crash between publish and ledger insert.
3. **Coordinator.** Take an OS-held, nonblocking lock scoped to the store for the whole acquisition command. Skip overlapping invocations without touching import state. Resume pending work before considering newer arrivals. Dispatch through the same import runtime and mark complete only on a successful terminal report, including an all-skipped import. Pin a crash after import and before completion, import failure, a renamed duplicate, and a retry with the inbox copy gone. For fresh acquisitions with comparable production evidence, reject an archive with a production time strictly earlier than the latest completed one to avoid replaying stale conversation revisions. When the ordering is unknown, process in first-observed order and document that the inbox is for fresh exports.
4. **Operator integration.** Add `acquire-chatgpt` and the read-only status projection. Describe setup, scheduler failure logging, quarantine of a bad inbox file, and manual recovery. Validate the new flow using the [quickstart](quickstart.md), including the existing manual and replay entry points.

Each implementation slice starts with a failing test and runs that test to green before integration. The [contract](contracts/acquisition.md) defines failure and status semantics. Phase 2 generates the task list after plan approval.
