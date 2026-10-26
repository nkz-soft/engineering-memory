# Quickstart Validation: Local Raw Archive

## Prerequisites

Use Python 3.13 and uv from the repository root. Tests use synthetic history, a temporary local directory, and fake memory/import state; no private exports or live Hindsight instance are needed.

```powershell
uv sync --locked --group dev
```

## Contract and persistence validation

After implementation (these new test modules do not exist at the planning gate):

```powershell
uv run pytest tests/contracts tests/unit/test_local_archive.py tests/unit/test_archive_replay_source.py -q
```

Expected: both local and in-memory implementations pass shared archive semantics; a fresh local instance retrieves every normalized field and exact original bytes. Failure injection verifies complete old/new publication, appropriate retryability, and safe diagnostics. Malicious IDs and symlinked record/version paths cannot escape the root. Independent readers see complete records while one writer replaces them.

## Replay acceptance

```powershell
uv run pytest tests/integration/test_archive_replay.py -q
```

The tests first create synthetic ChatGPT exports, import through the real parser/sanitizer/classifier into `LocalRawArchive`, and record expected identities/timestamps. They then delete the source export, reopen the archive, and pass `ChatGPTArchiveSource` through the same integration pipeline with fresh fake state and memory.

Expected: all valid conversations are retained again from originals with stable IDs/timestamps; current sanitization and classification run. Change a sanitizer rule between runs and verify replay reflects the new rule, proving it did not use the old normalized form. Inject a bad original before a good record and verify the failed document is reported while the good one imports. Empty replay produces no failures. Archive storage failure must prevent retention for that conversation.

## Full regression and static checks

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Expected: all checks pass, including existing interface import isolation and normalized-boundary constraints. Record actual command results during implementation, not claims based on this guide. Run filesystem behavior on supported Windows and Linux local storage; state any unverified platform limitations in the PR. No CLI replay command is introduced by this feature.
