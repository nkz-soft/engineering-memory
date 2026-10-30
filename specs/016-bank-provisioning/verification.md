# Verification: Bank Provisioning

## Test-first evidence

- Adapter suite initially failed collection because provision.py did not exist; after implementation 17 adapter checks passed.
- CLI checks then failed with `No such command provision`; wiring made all 21 focused checks pass.
- Full suite exposed the import guard's missing CLI composition exception. A focused test reproduced the missing exception before the guard was adjusted. CLI store imports and ingestion provisioning imports remain rejected.
- Review reproduced an uncaught non-ASCII token UnicodeEncodeError. Adapter now catches UnicodeError with a fixed safe message; adapter and CLI secret-canary checks pass.
- Focused final checks: `.venv/Scripts/python.exe -m pytest tests/unit/test_bank_provisioning.py tests/unit/test_provision_cli.py tests/structure/test_memory_implementation_boundary.py -q`: 31 passed before final test-only formatting.

## Review

Independent review found two issues: malformed-token exception leakage and missing live memory-preservation assertions. Both were fixed. Follow-up review reports no further actionable findings.

## Initial live attempt — superseded by successful validation below

`ENGINEERING_MEMORY_LIVE_STORE=1 .venv/Scripts/python.exe -m pytest tests/integration/test_bank_provisioning.py -q` was attempted: 1 failed with local connection refused (WinError 10061). No Hindsight container or local image was available. This is an environment prerequisite failure, not accepted live evidence. Do not mark the feature ready to merge until the test passes against pinned Hindsight 1.1.0 with config writes enabled and a configured extraction provider.

The live test covers initial missing-bank 404, exact mission, repeat configuration equality, no documents created by provisioning, a seeded synthetic document with positive extracted memory count, mission replacement, unchanged document snapshot/counts and unrelated reflection mission, with scoped cleanup. It never targets the production bank.

## Original acceptance prerequisite — resolved below

The original connection-refused prerequisite has been resolved by the isolated local validation recorded below. No actual history or production bank was changed.

## Final offline checks

- `.venv/Scripts/python.exe -m pytest -q`: **1739 passed, 18 skipped** in 61.07 seconds. Skips include opt-in live checks and existing platform/contract skips.
- `.venv/Scripts/ruff.exe check .`: all checks passed.
- `.venv/Scripts/ruff.exe format --check .`: 343 files already formatted.
- `uv build --wheel`: built engineering_memory-0.1.0-py3-none-any.whl. A zipfile assertion verified that engineering_memory/memory/hindsight/mission.txt is included.

Commands use the installed workspace interpreter because sandbox uv cache writes failed; the environment was created with `uv sync --locked --group dev`.

## Successful local live validation (2026-10-30)

Started an isolated `engineering-memory-provision-validation` Compose project using the repository-pinned Hindsight 1.1.0 and LiteLLM images, existing ignored provider configuration from worktree 16, and `HINDSIGHT_API_ENABLE_BANK_CONFIG_API=true`. Both services became healthy. No credentials were printed or committed.

Commands and outcomes:

```text
ENGINEERING_MEMORY_LIVE_STORE=1
ENGINEERING_MEMORY_LIVE_STORE_URL=http://127.0.0.1:8889
.venv/Scripts/python.exe -m pytest tests/integration/test_bank_provisioning.py -q --tb=short
1 passed in 12.76s
```

This running-instance test observed missing-bank 404, config-write bank creation, exact canonical mission read-back, unchanged repeated provisioning, zero documents after provisioning, successful real extraction of a synthetic document with positive memory count, mission replacement, preservation of the document snapshot/counts and unrelated reflection mission. The test deleted its generated scratch bank.

Additionally ran the installed `.venv/Scripts/engineering-memory.exe provision` twice with a separately generated `engineering-memory-provision-cli-<uuid>` bank: both exited 0 and printed `Bank retain mission verified.` That bank was deleted in cleanup. No production bank was provisioned or altered.

The isolated validation containers/network were stopped with Compose down without deleting volumes. The temporary config-write overlay was removed. The required live validation gate for issue #17 is now satisfied; this is provisioning acceptance, not full-product E2E.
