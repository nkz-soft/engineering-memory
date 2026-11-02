# Implementation Plan: Claude chat history source

**Branch**: `025-claude-chat-source` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)
**Input**: Issue #26; `specs/025-claude-chat-source/spec.md`.

## Summary

Add a Claude plain-chat reader and archive-original replay reader behind ConversationSource.
Register them through an explicit `import --source claude-chat` selector, preserving the ChatGPT
 default. The shared ingestion pipeline and all downstream policies remain unchanged.

## Technical Context

**Language/Version**: Python 3.13.
**Primary Dependencies**: Existing Pydantic v2, Typer and standard-library JSON/ZIP support; no new dependency.
**Storage**: Existing local raw archive and SQLite state, unchanged.
**Testing**: pytest unit, ConversationSource contract, pipeline/CLI integration and opt-in live recall.
**Target Platform**: Existing Windows/Linux operator CLI and Docker deployment.
**Project Type**: Modular monolith / CLI.
**Performance Goals**: Process conversation by conversation; do not materialize the entire export
or acquire attachments. No unsupported throughput promise; verify incremental consumption.
**Constraints**: Synthetic fixtures only; preserve originals; no contents in errors/logs; existing
sanitization before retention. Official export documentation does not specify a stable JSON schema.
**Scale/Scope**: One new plain-chat source; no Claude Code, live export acquisition or account API.

## Constitution Check

| Principle | Before research | After design |
|---|---|---|
| I — Raw archive | Pass: source supplies original record bytes | Pass: archive replay reparses originals; shared archival path unchanged |
| II — Provenance/identity | Pass: existing source enum, deterministic ids | Pass: native uuid and original timestamps, generic tags/hash skip |
| III — Test-first | Pass: no implementation in planning | Pass: each task must observe failing parser/contract/integration tests before code; live import/recall gate retained |
| IV — Replaceable boundaries | Pass: ConversationSource only | Pass: runtime registration selects readers; pipeline/domain/memory/access unchanged |
| V — Secrets | Pass: reuse sanitizer | Pass: no payload-bearing diagnostics; synthetic secret verifies retention/access redaction |

No principle, stack, bank, tag or Hindsight contract changes. New source requires its own ADR:
proposed ADR-009 below. Confirm the next available number at implementation time (ADR-007 is
reserved and ADR-008 exists). Implementation validation requires a patch amendment (1.3.1) recording claude_chat in the
constitution module tree; no principle or policy changes.

## Project Structure

### Documentation (this feature)

`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/source.md`, `quickstart.md`,
and `checklists/requirements.md`. `tasks.md` is generated only after human approval.

### Source Code (repository root)

- `src/engineering_memory/ingestion/claude_chat/`: export source, parser, archive source and exports.
- `src/engineering_memory/cli/__init__.py`: source option/help, defaulting to chatgpt.
- `src/engineering_memory/cli/runtime.py`: source-reader registration for exports and replay.
- `tests/unit/`, `tests/contracts/`, `tests/integration/`, `tests/fixtures/`: source and composition checks.
- `ARCHITECTURE.md`: append the accepted source ADR at implementation; update operator-source documentation.

**Structure Decision**: CLI selector and runtime composition are the registration allowed by #26.
No shared stage, domain model, memory implementation or persistence schema changes. Reuse the
existing JSON record scanner unchanged, despite its ChatGPT package location; constrain export
packaging in the Claude module rather than changing ChatGPT behavior.

## Delivery and Verification Design

1. Establish synthetic export dialect fixtures and fail parser tests first: native id/time,
   roles/order, text/content precedence, missing/invalid fields, attachments and unknown blocks.
2. Fail and pass all CS-1–CS-7 contract checks against the real Claude reader, including resuming
   after an error and preserving original JSON slices. Test streaming and resource cleanup.
3. Fail and pass Claude archive-original replay, unchanged skip, changed-content update, force,
   dry-run and secret handling through the existing pipeline.
4. Fail and pass explicit CLI source selection and unknown/unsupported source refusal before
   side effects; retain ChatGPT defaults. Register both export and archive readers.
5. Import distinct synthetic Claude/ChatGPT facts, including matching native ids across sources,
   then recall unfiltered/by source and open sanitized Claude content. Include an opt-in live
   Hindsight run to verify actual tags, ids and retrieval semantics rather than only fakes.
6. Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`; record commands and
   outcomes and perform code review before opening a PR. Missing live configuration must be
   reported as unverified, never represented as a passed live check.

## Decision Record — Proposed ADR-009: Claude plain-chat source

**Status**: Proposed for the Phase 1 gate; to be appended to ARCHITECTURE.md during implementation.
**Context**: The constitution requires an independent source and ADR. Claude exports are available,
but the official user help does not publish a JSON schema. The pipeline already carries generic
source identity; CLI registration is the only missing composition point outside the new module.
**Decision**: Support a bounded, synthetic-fixture-defined conversations.json dialect described in
[data-model.md](data-model.md). Use a new ClaudeChatExportSource and ClaudeChatArchiveSource with
an explicit source selector. Keep parsing, format policy and replay inside the new module. Use
existing normalized models, record scanning, sanitization, archive, state and memory contracts.
Preserve original records, including unknown fields; no schema is claimed to cover all exports.
**Alternatives considered**: Folding Claude into ChatGPT parsing violates format ownership.
Automatic format guessing risks accepting the wrong dialect; explicit selection is predictable.
Extracting a new shared parser package would expand runtime scope without a current need.
A separate pipeline would duplicate security and identity policy. Live acquisition/Compliance API
is a different feature and format.
**Consequences**: Small CLI registration changes are necessary. Unsupported export variants fail
explicitly; a local user export may expose additional variants that require fixtures before
support. No private export is needed or committed for this planning phase.

## Complexity Tracking

No constitution deviations. The deliberate dependency on the existing JSON scanner is bounded,
unchanged, and tested via source contracts; defer moving it to shared code to separate work.
