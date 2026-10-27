# Verification: Local Raw Archive

**Date**: 2026-10-26. Feature `012-local-raw-archive`, issue #13.

## Test-first evidence

- Baseline `uv run pytest -q`: 1,455 passed, 2 skipped.
- New shared enumeration contracts: 3 failed because enumeration was absent, then all 12 archive contracts passed against the updated in-memory implementation.
- New local filesystem scenarios: 26 failed because local storage was absent; they passed after implementation (symlink permission skips on Windows are stated below).
- Original-based replay: 11 failed before the source existed, then passed through the real parser/sanitizer/classifier and local archive.
- Later regressions were each observed failing before their fixes: transient Windows sharing errors; boolean/float format versions coerced to 1; invalid-root enumeration repeating forever; initial replay listing failures repeating forever; malformed message roles leaking TypeError; Windows parent-component roots failing with error 123. Each focused rerun passed after its fix.
- Shared archive/source contracts run against the local/in-memory storage and the replay source. A deliberately empty enumeration is rejected by the contract guard.

## Final Windows verification

Python 3.13.15 on Windows local storage:

```text
uv run pytest -q -rs
1527 passed, 4 skipped in 27.88s

uv run ruff check .
All checks passed!

uv run ruff format --check .
275 files already formatted

git diff --check
exit 0
```

Two skips are existing optional failure hooks for the tag-indexed fake memory store (`tests/contracts/store.py`). Two are local symbolic-link tests because this Windows account lacks link-creation permission. Windows junction redirection, concurrent reads/replacements, bounded sharing retries and parent-component paths passed. Linux runs exercise the symbolic-link cases on native temporary storage.

## Linux verification setup

WSL Ubuntu uses Python 3.13.17 with an isolated uv environment below ignored `data/validation/`; pytest temporary archives are on Linux-native `/tmp`, not the mounted checkout. The Windows worktree's `.git` pointer contains a Windows path, so Linux Git metadata tests need the equivalent explicit environment:

```sh
export GIT_DIR=/mnt/d/Projects/open-source/nz/hermes-memory/.git/worktrees/13
export GIT_WORK_TREE="$PWD"
export UV_CACHE_DIR="$PWD/data/validation/cache"
export UV_PYTHON_INSTALL_DIR="$PWD/data/validation/python"
export UV_PROJECT_ENVIRONMENT="$PWD/data/validation/venv"
data/validation/bin/uv run --python 3.13 pytest -q -rs
```

An initial full Linux run without that Git override had two failures in `tests/structure/test_environment_files.py` because Linux could not read the Windows Git pointer, while 1,522 tests passed. No repository configuration was changed to address the environment mismatch. A corrected full run passed 1,526 tests with 4 skips before the final Windows-only parent-component regression was added.

Final corrected Linux run after all review fixes and the Windows path regression:

```text
data/validation/bin/uv run --python 3.13 pytest -q -rs
1526 passed, 5 skipped in 39.35s
```

The five skips are the two existing optional fake-store failure hooks and the
three Windows-only junction, sharing-retry and extended-path tests. Both Linux
symbolic-link rejection cases and POSIX synchronization paths passed.

## Independent review

A read-only reviewer inspected all implementation, tests, contracts, atomic publication, durability/error paths, safe diagnostics and replay integration. Three confirmed findings were fixed with red/green regression tests: terminal replay initialization, malformed parser values and Windows dot-segment normalization. The reviewer then reported no remaining critical, important or minor findings, conditional only on final suite verification.

The reviewer explicitly excluded universal power-loss resilience, hostile concurrent directory replacement, encryption, multi-writer/network storage, historical revisions and production orchestration, matching the documented scope. Separate form reads spanning a replacement may observe different revisions, as the contract states.

## Limits

Durable paired records are tested across fresh instances/process exit semantics, not physical power interruption. One writer per root and independent readers are supported. Original content stays unsanitized locally; callers sanitize the normalized form before storing and before retention. Deliberate rule-change replay uses fresh import state. This feature adds neither production orchestration nor a replay CLI.

## Workflow completion — 2026-10-27

Implementation commit `60eb8f2` is published in
[PR #52](https://github.com/nkz-soft/engineering-memory/pull/52), attached to the
Codex chat. Issue #13 is labeled `in-review` and no longer `in-progress`.
GitHub CI on that implementation commit passed all three checks: lint/format/tests,
secret scan and container image. The PR is open and mergeable; merging remains
outside the issue-to-pr workflow. The worktree is retained for review.
