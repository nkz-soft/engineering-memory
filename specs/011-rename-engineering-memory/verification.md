# Verification: Engineering Memory rename

## Test-first evidence

- `uv run pytest -q tests/unit/test_settings_namespace.py` before implementation: 5 failed. The dedicated namespace was ignored and consumer-only values were accepted.
- `uv run pytest -q tests/unit/test_settings_namespace.py tests/unit/test_settings_loading.py` after prefix isolation: 19 passed.
- `uv run pytest -q tests/unit/test_cli.py tests/structure/test_packaging.py tests/structure/test_image_definition.py tests/structure/test_ci_workflow.py` after changing expectations, before renaming implementation: 3 failed, 22 passed (CLI identity, console-script declaration and image entrypoint).

## Local final verification

- `uv sync --locked`: passed; installed renamed project and removed the former editable distribution.
- `uv run pytest -q`: 1455 passed, 2 skipped in 22.02s. The two pre-existing cost/streaming checks are intentionally opt-in.
- `uv run ruff check .`: all checks passed.
- `uv run ruff format --check .`: 258 files already formatted.
- `git diff --cached --check`: passed.
- `uv run engineering-memory --help`: usage printed; exit 0.
- `uv run engineering-memory --version`: `engineering-memory 0.1.0`; exit 0.
- `uv build`: source distribution and wheel built successfully.
- `uv venv .venv-wheel` and `uv pip install --python .venv-wheel/Scripts/python.exe dist/engineering_memory-0.1.0-py3-none-any.whl`: clean non-editable installation succeeded.
- Clean-install command help and version passed. Python assertions confirmed distribution version 0.1.0, package resolution under site-packages and absence of the former import package. Temporary environment removed after inspection.
- Tracked case-insensitive project-identifier audit: no old project identifiers. Former consumer-prefix references remain only in negative-test inputs and environment-isolation fixtures.

## Review and repository

Independent read-only code review found no blocking correctness or security issue. The only documentation finding (a self-to-self rename instruction in the plan) was fixed. Data paths, serialized models and stable identities are unchanged.

The GitHub repository rename succeeded. Canonical repository `nkz-soft/engineering-memory` and the former API endpoint resolve to the same repository ID, 1367188302. The former web URL returns HTTP 301 with Location pointing to the canonical repository. Origin now uses the canonical URL. No checkout directory was renamed.

## Container verification

Local `docker version` and `docker --context desktop-linux version` could not reach their engine pipes. No local image build/run success is claimed. The existing CI Container image job builds, runs default help and checks non-root execution and artifact contents. Its result will be recorded after the PR run.
