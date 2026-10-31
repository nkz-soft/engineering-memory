# Implementation Plan: Operator command line

**Branch**: `020-operator-cli` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)
**Input**: Issue #21

## Summary

Extend the existing Typer application with import and status, retain provision, and establish text/JSON and exit-code contracts. The CLI composes concrete adapters; the pipeline remains interface-driven. Stop after this design for human review.

## Technical Context

**Language/Version**: Python 3.13.
**Primary Dependencies**: Existing Typer, Pydantic v2, SQLAlchemy 2, httpx, Tenacity and observability helpers; no new dependency.
**Storage**: Existing local archive and SQLite import state. No new run ledger/schema.
**Testing**: pytest with Typer CliRunner, existing synthetic corpus and real local storage; opt-in live instance tests.
**Target Platform**: Existing Windows/Linux environments and Docker console entry point.
**Project Type**: Local CLI in modular monolith.
**Performance Goals**: Preserve conversation-by-conversation source consumption; status lists existing records, without loading original conversations.
**Constraints**: Single state writer; offline read-only status; sanitized diagnostics; explicit provisioning.
**Scale/Scope**: One shared bank and ChatGPT export/archive inputs. Status may enumerate current records; pagination is deferred until measured need.

## Constitution Check

Pre-research and post-design gates both PASS:

1. Raw archive: compose the existing pipeline; originals and sanitized normalized forms precede retention. Replay reads originals through ChatGPTArchiveSource.
2. Provenance/identity: preserve existing enrichment and may_skip, deterministic document ids, original timestamps and force semantics.
3. Test-first: implementation must observe failing CLI tests before adding each command/format/error path; preserve boundary suites and add live fixture command coverage. No implementation or tests are claimed at this planning gate.
4. Replaceable boundaries: CLI composition may construct adapters; pipeline/status services depend on protocols. Add enumeration to ImportState and its SQLite/fake contracts rather than issuing SQL from commands. Keep Hindsight operations inside memory/hindsight.
5. Secrets: fixed diagnostics, safe report fields, existing sanitizer, no credential flags or arbitrary exception rendering. Status never reads conversation content or connects to memory.

Stack and bank policy unchanged; no governance decision record or deviation required. Issue scope fits architecture sections 21–22.

## Project Structure

Feature artifacts: spec.md, plan.md, research.md, data-model.md, contracts/cli.md, quickstart.md, checklists/requirements.md. tasks.md is deferred until approval.

Source changes:
- `src/engineering_memory/cli/`: retain app/entry point; extract composition and result rendering as needed to keep command callbacks small.
- `src/engineering_memory/ingestion/state.py`: add read-only latest-record enumeration protocol contract.
- `src/engineering_memory/ingestion/sqlite_state.py`: implement ordered validated enumeration without initialization on status reads.
- `tests/unit/`: CLI validation/output/composition/resource tests, including existing provision compatibility.
- `tests/contracts/` and `tests/fakes/state.py`: enumeration contract and replaceable fake.
- `tests/integration/`: command-level synthetic export/replay/state coverage and explicit opt-in live scenario.
- `README.md` and `ARCHITECTURE.md` section 20: publish the agreed surface and close the deferred command decision.

## Implementation Approach

1. Write failing CLI contract tests for help/version, source exclusivity, exit codes and JSON shape. Preserve existing provision invocation and console entry point.
2. Write failing boundary tests for deterministic enumeration (source, source_id), empty/missing/corrupt state, and cleanup. Add `ImportState.iter_records()` and implement SQLite query over current rows using existing schema validation and error mapping. Update fake and contract consumers. Do not persist skips.
3. Build composition only in CLI layer using existing Settings, source adapters, sanitizer, deterministic classifier, LocalRawArchive, SQLiteImportState, memory store and IngestionPipeline. Confirm constructors and cleanup conventions during implementation. Import may initialize state; status must not. Use narrow local path settings for offline status without weakening full validation for imports/provision.
4. Delegate provision to existing memory/hindsight provision service. Add shared safe result rendering without changing its successful default text unnecessarily. Do not auto-provision during import.
5. Serialize RunReport explicitly (computed counts/status are properties, not automatically serialized fields). Map all item/terminal failures to nonzero; keep structured stdout clean and logging on stderr. Catch known boundary/settings errors and contain unexpected exception messages at the CLI boundary; handle interrupts with cleanup and exit 130.
6. Add status using only import-state boundary enumeration; list latest records with safe stage categories, never trust arbitrary persisted error text for display. Missing DB is empty; invalid existing DB is failure. Prove no creation, migration or writes during inspection.
7. Add command-level persistent fixture runs for initial/unchanged/changed/force/replay and failure continuation, then opt-in live fixture validation including provisioning and status. Update docs and architecture surface together.

## Validation Strategy

Red → green for each slice. Test text and JSON for every operational command, absent/conflicting sources, empty/all-skipped/partial/terminal failure, safe unexpected exceptions and resource cleanup. Use synthetic secret sentinels in inputs and error messages. Assert offline status works without network settings or requests and leaves storage untouched. Verify existing provision/version tests and packaging entry point. Live tests use configured scratch infrastructure and synthetic histories only; never real exports in committed artifacts.

Commands are listed in quickstart.md; execution belongs to Phase 2. Completion requires recorded live results, not merely skipped integration tests.

## Alternatives Considered

- FastAPI control surface: rejected by issue #21 and ADR-004; local CLI is the MVP surface.
- New run-history database: rejected as unnecessary scope and incompatible with current latest-state semantics; report skips per invocation.
- SQL inside CLI: rejected because status must preserve the import-state boundary.
- Automatic provisioning on import: rejected; violates explicit provisioning policy.
- One import command per source mode: rejected in favor of mutually exclusive options on one command; keeps force and result semantics uniform.

## Complexity Tracking

No constitutional violations. The only boundary extension is read-only current-record enumeration, necessary to answer status without coupling to SQLite.
