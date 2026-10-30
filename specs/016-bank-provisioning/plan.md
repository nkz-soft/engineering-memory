# Implementation Plan: Bank Provisioning

**Branch**: `016-bank-provisioning` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)
**Input**: Issue #17

## Summary

Add `engineering-memory provision` to create the configured bank and apply the canonical retain mission, then verify exact read-back. Keep all engine routes and payloads in `memory/hindsight`; the CLI delegates to that administrative adapter. Provisioning is separate from MemoryStore retention and does not write conversation data.

## Technical Context

**Language/Version**: Python 3.13.
**Primary Dependencies**: Existing Typer, Pydantic settings and httpx; no additional runtime packages.
**Storage**: Existing self-hosted Hindsight bank configuration; no archive/state schema changes.
**Testing**: pytest, httpx.MockTransport, Typer CliRunner, existing live integration conventions.
**Target Platform**: Existing local Windows/Linux CLI and Docker deployment.
**Project Type**: Modular monolith with CLI.
**Performance Goals**: Bounded administrative operation, default overall deadline 60 seconds and per-request timeout at most 30 seconds; no extraction calls.
**Constraints**: Single shared production bank; exact mission read-back; preserve unrelated settings; environment credentials; no response-body logging.
**Scale/Scope**: One bank per invocation; no batch or multi-bank management.

## Constitution Check

Pre-research and post-design review: PASS; no deviations.

1. Raw archive: no history is imported or fabricated, and provisioning never creates memory items. Existing originals remain untouched.
2. Provenance/identity: no document identities, timestamps, tags, or import state change.
3. Test-first: observe failing tests before each implementation slice; live acceptance supplements rather than replaces unit tests.
4. Replaceable boundaries: bank administration remains inside `memory/hindsight`; CLI wiring may construct the adapter as it already constructs engine-specific dependencies. Domain, ingestion, access and MemoryStore protocol remain free of bank configuration vocabulary.
5. Secrets: use existing environment-backed credentials, reject unsafe URLs and redirects, disable environment proxy inheritance consistent with #16, and emit fixed safe errors without raw exceptions or response bodies.

Stack and governance: no new source, stack change, bank policy change or ADR required. This implements ADR-003. Review the actual pinned API before finalizing wire payloads; any architecture discrepancy requires an explicit correction rather than an assumption.

## Project Structure

```text
specs/016-bank-provisioning/
  spec.md, plan.md, research.md, data-model.md, quickstart.md
  checklists/requirements.md
  contracts/provision.md
src/engineering_memory/
  cli/__init__.py                     # register provision command
  memory/hindsight/provision.py       # bounded admin operation and canonical mission
  memory/hindsight/mission.txt        # exact Architecture §12 text
  settings/                          # reuse existing settings without schema changes
 tests/unit/test_bank_provisioning.py
 tests/unit/test_provision_cli.py
 tests/integration/test_bank_provisioning.py
 docs/development/local-hindsight.md
```

**Structure Decision**: A focused administration adapter avoids extending the consumer memory boundary with engine configuration. Package the mission as a resource and assert its exact equality to Architecture §12, including whitespace. CLI imports no HTTP paths or payload fields.

## Implementation and Verification Sequence

1. Inspect pinned v1.1.0 OpenAPI/source and prove creation/config paths using a unique scratch bank. Never use retain as a bank-creation shortcut. Reuse existing authenticated local deployment. Confirm actual field name and conflict behavior before coding transport assertions.
2. Write failing tests for canonical mission packaging/equality, explicit creation, minimal configuration update, read-back and repeat invocation. Implement bounded adapter calls with percent-encoded bank paths and safe errors. A 404 permits creation; authorization/transport failures do not.
3. Write failing preservation, partial-failure/rerun, mismatch, malformed response, redirect, timeout and secret-canary tests; implement safe convergence. No destructive compensation. Limit retries to operations proven safe; rerun always remains supported.
4. Write failing CLI registration/settings/exit-code/help tests, then wire the command. Update the existing CLI shell test to assert the newly specified command. Document provision-before-import and mission evolution.
5. Add opt-in live tests proving prior 404, exact read-back, repeat convergence, preservation of unrelated configuration and seeded synthetic memories, then cleanup only the unique scratch bank. Test a changed synthetic mission through an internal test seam, without public arbitrary-mission input.
6. Run `uv run pytest`, `uv run ruff check .` and `uv run ruff format --check .`; run live integration tests with configured local engine and record exact results. If the engine is unavailable, explicitly leave live acceptance unverified. Request code review before PR creation in Phase 2.

## Alternatives Considered

- Per-retain mission: rejected by ADR-003 and §9; the mission is bank-level configuration.
- Retain a dummy memory to create the bank: violates archive provenance and incurs extraction; use dedicated bank creation.
- Add provisioning to MemoryStore: leaks engine administration into the replaceable data boundary.
- Replace all bank configuration: risks overwriting unrelated settings; patch only the mission and verify it.
- Automatically re-extract existing memories: exceeds #17 and belongs to archive replay.

## Complexity Tracking

No constitutional violations or additional layers requiring justification.

## Review Gate

Planning only. Do not generate tasks, implement or open a PR until the human approves this committed plan. No live behavior is claimed as verified in this planning phase.
