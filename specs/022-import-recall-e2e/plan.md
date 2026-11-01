# Implementation Plan: Import and recall end to end

**Branch**: `022-import-recall-e2e` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)
**Input**: Issue #23 and specs/022-import-recall-e2e/spec.md

## Summary

Close the assembled-system coverage gap with a required live end-to-end gate. Import a synthetic ChatGPT export through the real CLI and adapters, then recall its decision and verify identity, provenance, complete tags and original temporal grounding. Provision the pinned engine and synthetic extraction fixture through testcontainers, independently of the existing Compose contract gate.

## Technical Context

**Language/Version**: Python 3.13, uv.
**Primary Dependencies**: Existing Typer, Pydantic, httpx, SQLAlchemy and pytest; add testcontainers-python to the dev group without displacing another stack entry.
**Storage**: Temporary local archive, SQLite state, ephemeral live-engine database.
**Testing**: pytest live end-to-end suite, assertion negative controls, runner/report completeness tests, lint and formatting.
**Target Platform**: Linux CI with Docker; Docker-capable local developer machines.
**Project Type**: Modular monolith CLI with external memory engine.
**Performance Goals**: Startup at most 600 seconds, pytest subprocess at most 420 seconds, cleanup at most 90 seconds, CI job at most 25 minutes; recall polling bounded within the test deadline.
**Constraints**: No credentials or real histories; exact existing image digest; no changes to domain or memory protocols.
**Scale/Scope**: One small conversation per clean run; Phase 1 item 11 only.

## Constitution Check

Pre-research and post-design gates both PASS:

| Principle | Compliance |
|---|---|
| I — Raw archive | Real archive adapter persists original and sanitized normalized records; test verifies both. |
| II — Provenance | Compare independent expected identity/provenance and inspect engine tags, original wire time and metadata time. Include omission controls. |
| III — Test-first | Write failing suite/runner controls first, observe failure, implement harness and fixes, then verify green. No implementation in this planning phase. |
| IV — Replaceable boundaries | Use real orchestration and memory adapter; engine-specific inspection remains exclusively in integration tests. No public interface expansion. |
| V — Secrets | Synthetic corpus and local deterministic extraction only; temporary storage, no credentials, test-owned bank cleanup. |

Stack remains fixed. Testcontainers is the already prescribed integration-test tool. Disposable banks are test isolation, not a production bank strategy change. No ADR or constitution amendment needed.

## Project Structure

```text
specs/022-import-recall-e2e/
  spec.md
  plan.md
  research.md
  data-model.md
  contracts/e2e.md
  quickstart.md
  checklists/requirements.md
tests/integration/test_import_recall_e2e.py    # new live case and evidence checks
tests/integration/hindsight_contract/llm.py  # reuse extraction fixture
tests/unit/test_e2e_runner.py               # new completeness/deadline controls
deploy/hindsight/e2e.py                     # new testcontainers runner
.github/workflows/ci.yml                    # required live end-to-end job
pyproject.toml / uv.lock                    # dev-only testcontainers dependency
```

**Structure Decision**: Separate end-to-end runner leaves the existing §6/9/10 Compose contract gate intact. The new runner owns a disposable Docker network, dynamically mapped ports, engine and fixture containers, readiness checks and teardown. Reuse the current pinned image and fixture protocol; avoid creating a second extraction simulation.

## Design and execution

1. Create an independently specified synthetic decision with historical time, project and repository cues. Define expected provenance and tags as literals rather than deriving them from serializer output.
2. Start fixture and engine containers on a unique test network with temporary storage and dynamic ports. Supply the fixture URL over that network; require readiness before starting pytest. Provision a unique scratch bank with the normal command.
3. Invoke ordinary import using the real parser, sanitizer, classifier, enrichment, archive, state and memory store. Confirm successful state and archived forms. No memory mocking on the positive path.
4. Recall through HindsightStore with expected tags. Compare known decision terms and every exposed provenance field. Supplement with raw engine evidence for document_id, complete tags, original mentioned_at and metadata started_at. The public RecallResult intentionally does not expose tags or original time.
5. Query disjoint scope and individual required tags to prove filtering. Use bounded polling only for eventual visibility, never to hide incorrect metadata.
6. Prove validators reject independently omitted provenance fields, each required tag and wire timestamp. For wire-time sensitivity, alter the real retain serialization in a separate isolated negative run and observe the temporal assertion fail; metadata time alone is insufficient. Keep destructive controls confined to disposable banks.
7. Add a required CI job that runs the new runner and checks exact required JUnit case identities, zero skips/errors/failures and nonempty results. Missing Docker, startup failure and timeout are failures in this mode. Ordinary offline pytest skips the opt-in live case explicitly.
8. Run lint, format, offline tests, existing contract gate and new end-to-end gate. Record actual red/green evidence. Repeat clean end-to-end execution and verify cleanup.

## Alternatives considered

- Retain acknowledgement only: rejected by the issue; extraction or retrieval can still be empty.
- Fake memory store: cannot prove assembled live behavior.
- Paid/external model in required CI: unsuitable for forks and introduces credentials and variability. Real-model quality remains separate evaluation work.
- Merely extend the current CLI substring test: insufficient metadata coverage and not selected by the current live CI runner.
- Broaden RecallResult solely for assertions: avoid changing a public contract when supplementary integration evidence suffices.
- Reuse Compose exclusively: valid for existing contracts, but this feature adopts the prescribed testcontainers lifecycle with isolated ports and resources.

## Complexity Tracking

No constitutional violations or deviations. Open implementation detail: choose the installed testcontainers API compatible with the locked dev dependency during implementation; preserve the lifecycle and deadline contract in contracts/e2e.md.

## Implementation refinement

The ordinary CLI does not accept known repository or optional user context. Keep its positive case intact and add a separately required real-pipeline case supplying those supported constructor arguments. This covers populated repository provenance and all four tag namespaces without a CLI feature or production contract change. Add a separate 90-second cleanup subprocess and best-effort label-scoped deletion to enforce the lifecycle deadline even after worker timeout.
