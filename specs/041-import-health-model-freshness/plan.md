# Implementation Plan — Import Health and Project-Model Freshness

**Branch** `041-import-health-model-freshness` | **Date** 2026-11-19 | **Spec** [Specification](spec.md)

## Summary

Add an authenticated Status panel to the local explorer. Persist the latest source outcome, last successful import and per-project import evidence in the existing SQLite state. Read model refresh metadata through a narrow memory interface and derive freshness without loading model excerpts or citations.

## Technical Context

- Python 3.13, Pydantic v2, SQLAlchemy 2 and SQLite for import state, FastAPI for the loopback explorer and existing browser HTML/CSS/JavaScript. No new dependencies.
- One aggregate per supported source and classified project. Use indexed lookups and bounded reads for the three model kinds in the selected project. Keep existing backend deadlines and distinguish source storage failure from model service failure.
- Verify with synthetic pytest unit, SQLite integration, HTTP contract and browser tests. Use the existing isolated live model suite for adapter semantics that depend on the running service.

## Constitution Check

| Principle | Before research and after design |
| --- | --- |
| I. Raw archive | The archive remains authoritative for conversation history. Health tables contain operational aggregates only. Archive write still precedes retention. Test import and replay through the normal pipeline. |
| II. Provenance and stable identity | Keep the existing document ID, hash skip, source time and tags. Track ingestion time separately. Test that an unchanged replay preserves the timestamp and that project comparisons use import time. |
| III. Test-first | After approval, observe the targeted tests fail for each slice before implementing it. Include SQLite and model-reader boundary contracts and an import-to-status integration case. Preserve import-to-recall coverage. |
| IV. Replaceable boundaries | Importers write through the import-state boundary. The explorer reads status through an access service and reader protocols. Only the existing memory adapter interprets backend model fields. The status operation is read-only. |
| V. Secrets | Use typed allowlists for persistence and transport. Do not copy exceptions, archive data or model content into status. Reuse authenticated loopback and no-store controls. Test with sentinels at write, response and browser boundaries. |

Both checks pass without deviations. This is Phase 3 on the existing ADR-014 explorer. Architecture §§21–22 and ADR-012 allow this scoped read of importer-maintained model metadata. The issue supplies no governance ticks and the design proposes no governance change.

## Project Structure

- `ingestion/state.py`, `ingestion/sqlite_state.py` and a focused `ingestion/health.py` define aggregates, migration and read/write contracts. `ingestion/pipeline.py` records committed import evidence. `cli/runtime.py` records source attempts from the two shared command paths.
- `memory/interface/project_models.py` defines a metadata-only reader. `memory/hindsight/project_models.py` implements the reader using the existing model lookup and validated fields, bypassing evidence expansion.
- `access/status.py` combines operational reads. `cli/explorer.py` wires the state and model readers. `api/explorer.py` and its bundled `explorer_assets/` expose the status request and view.
- `tests/integration/test_persistent_import_state.py`, a focused import-health integration suite, `tests/unit/test_project_models_store.py`, `tests/contracts/test_explorer_http.py` and `tests/integration/test_explorer_browser.py` cover the boundaries. Document interpretation in the existing explorer operator guidance.

## Alternatives Considered

The issue leaves alternatives unspecified. [Research](research.md) evaluates deriving status from existing per-conversation rows, using a standalone ledger or adding a metadata-only route to the existing explorer. The proposed design uses the existing state database and explorer.

## Implementation Sequence After Approval

1. Start with migration and transaction tests for fresh databases and v1/v2 state, retry and concurrent updates. Add aggregate read/write capabilities. Atomically update source success and the classified project's latest import when recording a successful retained conversation. Keep error and attempt data separate so later failures preserve success.
2. Start with CLI integration tests for all four sources, including one successful source and one source-level failure surviving restart. Cover mixed outcomes, deferred-only scans, retry after failure, no-op and dry-run behavior. Record safe outcomes once per actual source attempt at the shared runtime entry points. Keep the existing CLI output and exit-code contracts.
3. Start with model-adapter and freshness tests. Reuse bounded model lookups and legacy model identity fallback. Build a projection that returns refresh state, timestamps and tri-state freshness evidence. Verify no support resolution or model text is required. Preserve a source snapshot when a model read fails.
4. Start with HTTP auth and browser tests for the status panel, scope changes, lock and privacy. Use the existing protected dispatch for `POST /api/status`. Render timestamps and fixed labels as text. Clear the panel on lock and prevent stale requests from rendering after lock or project change.
5. Run the [validation guide](quickstart.md), record the observed results and document the status semantics.

Follow red → green → refactor for each slice. See the [data model](data-model.md) and [HTTP contract](contracts/status.md).

## Review Focus

- A failed forced re-import may overwrite an existing conversation row. Verify that the most recent confirmed source and project imports remain available.
- A crash or write failure can leave an attempt incomplete. Verify that prior status stays readable, a completed attempt is never invented, and a failed metadata commit cannot become a confirmed import.
- An old model on a fresh or upgraded state store has limited local evidence. Test missing timestamps, unknown backend freshness, equal timestamps and an unrelated project's import.
- Both manual and scheduled imports may report the same source. Verify that an earlier completion cannot overwrite a later recorded outcome, and a later failure cannot lower the successful import timestamp.
- A model backend can fail or send malformed metadata. Verify that valid source status and other model states still render, and that details never leave the adapter.
