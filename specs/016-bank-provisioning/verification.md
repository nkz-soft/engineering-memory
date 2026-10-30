# Verification: Bank Provisioning

## Test-first evidence

- Adapter suite initially failed collection because provision.py did not exist; after implementation 17 adapter checks passed.
- CLI checks then failed with `No such command provision`; wiring made all 21 focused checks pass.
- Full suite exposed the import guard's missing CLI composition exception. A focused test reproduced the missing exception before the guard was adjusted. CLI store imports and ingestion provisioning imports remain rejected.
- Review reproduced an uncaught non-ASCII token UnicodeEncodeError. Adapter now catches UnicodeError with a fixed safe message; adapter and CLI secret-canary checks pass.
- Focused final checks: `.venv/Scripts/python.exe -m pytest tests/unit/test_bank_provisioning.py tests/unit/test_provision_cli.py tests/structure/test_memory_implementation_boundary.py -q`: 31 passed before final test-only formatting.

## Review

Independent review found two issues: malformed-token exception leakage and missing live memory-preservation assertions. Both were fixed. Follow-up review reports no further actionable findings.

## Live acceptance — pending

`ENGINEERING_MEMORY_LIVE_STORE=1 .venv/Scripts/python.exe -m pytest tests/integration/test_bank_provisioning.py -q` was attempted: 1 failed with local connection refused (WinError 10061). No Hindsight container or local image was available. This is an environment prerequisite failure, not accepted live evidence. Do not mark the feature ready to merge until the test passes against pinned Hindsight 1.1.0 with config writes enabled and a configured extraction provider.

The live test covers initial missing-bank 404, exact mission, repeat configuration equality, no documents created by provisioning, a seeded synthetic document with positive extracted memory count, mission replacement, unchanged document snapshot/counts and unrelated reflection mission, with scoped cleanup. It never targets the production bank.

## Remaining acceptance

Run the documented opt-in test on the configured local engine. Draft PR remains appropriate until this constitution-required runtime check succeeds. No actual history or production bank was changed.

## Final offline checks

- `.venv/Scripts/python.exe -m pytest -q`: **1739 passed, 18 skipped** in 61.07 seconds. Skips include opt-in live checks and existing platform/contract skips.
- `.venv/Scripts/ruff.exe check .`: all checks passed.
- `.venv/Scripts/ruff.exe format --check .`: 343 files already formatted.
- `uv build --wheel`: built engineering_memory-0.1.0-py3-none-any.whl. A zipfile assertion verified that engineering_memory/memory/hindsight/mission.txt is included.

Commands use the installed workspace interpreter because sandbox uv cache writes failed; the environment was created with `uv sync --locked --group dev`.
