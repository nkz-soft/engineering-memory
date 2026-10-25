# Rename Validation Guide

Run from the issue worktree after implementation approval. Prerequisites: Python 3.13 via uv, authenticated gh and a working Docker daemon for image checks. Use synthetic configuration only.

## Test-first evidence

Run the newly added configuration isolation tests before changing the settings prefix; record failures. Run updated packaging/CLI identity assertions before renaming implementation; record failures. Then rerun each targeted suite after the matching change.

## Regression and installation

```powershell
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run engineering-memory --help
uv run engineering-memory --version
uv build
```

Expected: tests and Ruff pass, command help exits zero, version names Engineering Memory and matches distribution metadata, and build succeeds. Verify the built wheel in a clean environment so a stale editable installation cannot conceal missing package metadata.

## Configuration

Exercise dedicated-prefix success, conflicting and invalid inherited consumer settings, former-prefix-only failure, explicit environment-file loading and environment-over-file precedence. Use tests with controlled environment and temporary files; do not use private operator `.env` files. Existing default-path and safe-error tests must also pass.

## Container

```powershell
docker build -t engineering-memory:ci .
docker run --rm engineering-memory:ci
```

Expected: build succeeds; default invocation prints usage and exits zero. Repeat CI's checks for non-root execution, absence of development dependencies, tests and data. Preserve each command's exit code. An unavailable daemon is a missing check, not a passing image test.

## Identifier audit and repository

```powershell
git grep -n -i -E 'hermes[-_]memory'
git grep -n 'HERMES_'
git diff --check
git log --oneline origin/main..HEAD
```

Expected: no unexplained old project identifiers; old-prefix regression inputs are expected and reviewed contextually. Confirm Hermes consumer descriptions remain correct. Confirm no private data or unrelated commits appear.

After renaming the GitHub repository, query the canonical repository and the former API URL, verify both identify the same repository and the old URL redirects, and update origin to the canonical URL. Report any administration or CI limitations explicitly in the PR verification section.
