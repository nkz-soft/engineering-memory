# Quickstart Validation: Persistent Import State

This is the validation guide for Phase 2. The planning commit does not contain the adapter or its new tests; do not run the future focused commands against planning-only artifacts and report them as passing.

## Prerequisites

Python 3.13 and uv, with issue #14's worktree checked out on 013-sqlite-import-state. Fixtures are synthetic, storage uses temporary local paths, and no credentials, real export or Hindsight instance is needed. Install locked dependencies with `uv sync --locked` after implementation updates the lockfile.

## Focused checks after implementation

```powershell
uv run pytest tests/contracts/test_sqlite_state_passes_the_contract.py
uv run pytest tests/unit/test_sqlite_state.py tests/unit/test_import_state_rules.py
uv run pytest tests/integration/test_persistent_import_state.py
```

Expected: every IS contract including reopen succeeds; atomic rollback, corrupted/locked state and safe errors are tested; shared force policy agrees across adapters. Integration proves these outcomes:

| Scenario | Expected evidence |
|---|---|
| First import and reopened repeat | One initial retain, then zero new calls |
| Three unchanged refreshes | All skipped; success state preserved |
| One character changed | One additional retain, same document identity |
| Title/importer metadata only | No additional retain |
| Memory failure then rerun | Failed record survives reopen, retry retains, following unchanged run skips |
| Ordinary versus forced archive replay | Ordinary skips; force re-sanitizes from original and retains once |
| Missing or empty later export | Prior state/archive/bank preserved; no deletion calls |
| Lookup failure | Explicit failure; no retain |
| Interrupted record transaction | Prior complete outcome survives |

See [contract](contracts/import-state.md) for lifecycle and [data model](data-model.md) for persisted fields. At least one persistence test launches a fresh subprocess. Changed sanitization rules in forced replay must be observable in the retained payload, without storing real secrets in fixtures.

## Final verification after implementation

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv lock --check
git diff --check
```

Record actual commands and results in Phase 2 verification. Observe each new test fail before corresponding code. This issue validates memory-boundary calls with a fake; live retain/recall and production CLI remain separate work.

## Concrete adapter usage

The production importer in #19 composes this lifecycle (no CLI is introduced here):

```python
from engineering_memory.ingestion.sqlite_state import SQLiteImportState

state = SQLiteImportState(settings.import_state_path)
state.initialize()  # creates a new empty database, validates a compatible existing one
try:
    # Pass state through the ImportState protocol to the importer.
    # Reader-only composition calls state.validate() instead of initialize().
    ...
finally:
    state.close()
```

Reads and record writes open existing storage with SQLite URI mode=rw, preventing a missing database from being recreated by a reader. Construction is inert. A new adapter must explicitly initialize or validate before use. Keep one writer per local database; lock waits are bounded to five seconds. Persist safe errors only. Force bypasses the shared skip decision, while archive replay still uses original data and reapplies sanitization. Retain and local commit are separate operations, so partial failure can repeat extraction on a later run.
