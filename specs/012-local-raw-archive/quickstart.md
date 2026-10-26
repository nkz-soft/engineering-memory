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

## Implementation notes

Concrete storage is in `archive/local.py`; the private `archive/_windows.py`
module keeps Windows handle sharing and write-through replacement out of the
portable implementation and all boundary imports. File data is synchronized
before publication on both platforms. Directory metadata is synchronized on
POSIX. Process-restart durability is tested; no arbitrary-filesystem power-loss
guarantee is claimed. One writer and independent concurrent readers are supported.

Windows details were checked against Microsoft's primary documentation:
[MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw)
and [CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).
Sharing `DELETE` access permits replacement while a reader holds a record;
write-through is requested for publication. Bounded retry handles transient
access-denied/sharing statuses, which the concurrent-reader regression exposed.

Run the focused suites on Linux as well as Windows. The local tests use pytest's
temporary filesystem, so a Linux run under WSL exercises Linux-native temporary
storage even if the source checkout is mounted from Windows. Symlink tests may
skip on Windows without permission; Windows junction coverage requires no
symlink privilege. Windows-only sharing/junction tests skip on Linux.
