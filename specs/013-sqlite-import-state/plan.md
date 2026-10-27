# Implementation Plan: Persistent Import State

**Branch**: `013-sqlite-import-state` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: `/specs/013-sqlite-import-state/spec.md`, issue #14.

## Summary

Implement `SQLiteImportState` behind the existing protocol using SQLAlchemy 2 Core. Preserve `ImportRecord`, canonical hashing and stable identity. Add keyword-only `force=False` to the shared `may_skip` decision and exercise it in the existing test harness with persistent state and a real local archive. Production importer/CLI remain #19. Update architecture §§17/20 to reference the settled schema during implementation.

## Technical Context

**Language/Version**: Python 3.13.

**Primary Dependencies**: Add SQLAlchemy `>=2,<3` and regenerate uv.lock; existing Pydantic v2, pytest, standard-library sqlite3 error codes and pathlib. Synchronous Core; no async driver.

**Storage**: Existing `Settings.import_state_path`, default `data/import-state.db`; versioned schema, composite primary key. PostgreSQL adapter deferred behind unchanged protocol.

**Testing**: Reusable state contracts, persistence/transaction/fault/privacy tests, integration import and replay, full pytest and Ruff.

**Target Platform**: Local Windows/Linux filesystems and Linux container.

**Project Type**: Python modular monolith; library adapter, shared policy and test-harness integration; no command.

**Performance Goals**: Indexed lookup and one short transaction per record; one conversation at a time; no arbitrary latency SLA.

**Constraints**: Single writer, independent readers, five-second lock timeout, explicit disposal, complete committed records, safe errors, no membership diff or destructive recovery.

**Scale/Scope**: Years of personal history; current outcome only. No audit table, distributed locks, pruning or deletion API.

## Constitution Check

*Pre-research gate: PASS. Post-design gate: PASS. No deviations.*

| Principle | Compliance and evidence planned |
|---|---|
| I — Raw archive source of truth | Archive before retain; missing/empty export preservation; forced original-based replay re-sanitizes. State is bookkeeping, never original history. |
| II — Provenance and stable identity | Reuse source/native ID, original normalized hash and deterministic document ID. Reopen/change/skip tests prove extraction avoidance. |
| III — Test first | Observe failing contract, unit and integration tests before corresponding implementation. Planning introduces no implementation. |
| IV — Replaceable boundaries | Preserve record/find protocol. Adapter owns database imports/errors. Shared may_skip owns policy once. No Hindsight dependencies. |
| V — Secrets never reach memory | No stored bodies, parameter-bound SQL, echo disabled, fixed safe errors, synthetic fixtures; force still sanitizes before retain. |

Stack matches ADR-004. Scope is architecture §17, Phase 1 items 7–8. Governance selects none; no ADR or amendment needed.

## Project Structure

### Documentation (this feature)

```text
specs/013-sqlite-import-state/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/import-state.md
```

Generate tasks.md only after human approval.

### Source Code (repository root)

```text
src/engineering_memory/ingestion/
├── state.py                 # existing protocol/models; force-aware decision
└── sqlite_state.py          # adapter, schema/version and error translation
 tests/contracts/test_sqlite_state_passes_the_contract.py
 tests/unit/test_sqlite_state.py
 tests/unit/test_import_state_rules.py
 tests/integration/pipeline.py
 tests/integration/test_persistent_import_state.py
 pyproject.toml
 uv.lock
 ARCHITECTURE.md
```

**Structure Decision**: Keep boundary ownership in ingestion. Concrete adapter imports remain explicit; interface exports need not load SQLAlchemy. No second production pipeline.

## Design and Implementation Sequence

1. Write failing fixtures binding all ImportStateContract hooks to temporary SQLite files, including reopen, real locked and corrupt storage. Add SQLAlchemy with uv; implement the unchanged protocol.
2. Use [version-1 schema](data-model.md). Construction is inert. Explicit initialize() creates missing parents and only initializes empty/new storage. Validate existing compatible schema; reject foreign/partial/unsupported storage. Reader instances can validate existing storage without schema creation. find/record require initialized or explicitly validated storage.
3. Use bound SQLAlchemy Core expressions and engine.begin transactions. Under the supported single writer, SELECT then INSERT/UPDATE in one transaction avoids dialect-specific upsert and replacement deletes. Commit before record returns. Use Python 3.13 nonlegacy transaction control (`autocommit=False`), NullPool and short connections. Default SQLite journaling suffices; WAL is not a requirement. Lock wait is bounded at five seconds.
4. Serialize recorded_at as UTC ISO-8601 text with fixed microseconds and offset. Reconstruct through ImportRecord validation. Preserve opaque identifiers and stored strings exactly.
5. Translate by driver code/type: busy/locked/open/IO/resource failures become ImportStateUnavailable; invalid database, schema/version and malformed rows become ImportStateCorrupt. Do not classify all OperationalError as transient. Unknown database errors fail closed as corrupt. Fixed safe public messages; no raw exceptions or parameters in normal diagnostics.
6. Write failing shared decision tests, then add `may_skip(record, hash, *, force=False)`. Force always declines skipping. Harness `run(now=..., force=False)` passes it through; force bypasses equality only, never lookup errors or sanitization.
7. Write failing integration tests with real state and LocalRawArchive, synthetic input and counted fake memory store. Cover persistent multi-run skips, one-character and title-only changes, unsanitized hash, failed retry, forced original-based archive replay, missing/empty exports and state failures. Count retain calls because bank cardinality alone conceals duplicate extraction.
8. Update architecture §§17/20, dependency documentation and force contract. Hand adapter lifecycle and force behavior to #19; no CLI, production orchestration or retry loop here.

## Alternatives Considered

- Engine document upsert alone: explicitly rejected by #14/§17; extraction has already cost money.
- Hash redacted content or importer version: contradicts existing canonical contract and ADR-006; reapply rules with force.
- Persist skipped status: forbidden by ImportRecord; erases success and creates alternating re-extraction.
- Build #19 importer now: existing harness proves composition without expanding this issue.
- Dialect UPSERT, async driver, ORM sessions: unnecessary for a small synchronous single-writer boundary; portable Core statements suffice.
- PostgreSQL adapter, audit history, deletion scans or destructive repair: deferred or forbidden by scope/ADR-006.

## Verification Strategy

Observe each new test fail first, then pass. Run focused checks:

```text
uv run pytest tests/contracts/test_sqlite_state_passes_the_contract.py tests/unit/test_sqlite_state.py tests/unit/test_import_state_rules.py tests/integration/test_persistent_import_state.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv lock --check
git diff --check
```

Dispose the first adapter before reopen; include a fresh-subprocess persistence test. Inject failure after mutation before commit and verify the old committed record survives. Use independent reader connections; prove complete reads or explicit unavailable errors during contention.

No live Hindsight claim: integration uses the memory boundary fake. Production pipeline/live recall remains later work. A crash after retain but before state commit can repeat extraction; stable identity prevents duplicates, without promising exactly-once extraction across independent stores.

## Complexity Tracking

No constitution violations. Explicit version validation needs no migration framework. No tasks or implementation before approval.
