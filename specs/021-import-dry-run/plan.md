# Implementation Plan: Import dry run

**Branch**: `021-import-dry-run` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)
**Input**: Issue #22; specification in this directory.

## Summary

Add `import --dry-run` to preview either input source without memory-client construction,
network calls, archive writes or durable state changes. Share preparation and skip policy
with real ingestion; report safe per-conversation metadata even for predicted skips.

## Technical Context

**Language/Version**: Python 3.13.
**Primary Dependencies**: Existing Typer, Pydantic v2, SQLAlchemy 2 and structlog; no additions.
**Storage**: Existing SQLite state, read-only; local archive read-only for replay; ephemeral overlay.
**Testing**: pytest unit/integration/contract suites, synthetic fixtures, Ruff.
**Target Platform**: Existing local CLI and Docker runtime.
**Project Type**: Python modular monolith / CLI.
**Performance Goals**: Preserve sequential conversation processing; no additional remote work.
**Constraints**: No network or durable writes; safe output; preserve non-preview command contract.
**Scale/Scope**: Years of ChatGPT history; existing report accumulation remains, no new corpus copy.

## Constitution Check

| Principle | Before research | After design |
|---|---|---|
| I. Raw archive source of truth | Pass: preview imports nothing | Pass: no archive writes; real archive-before-retain order preserved |
| II. Provenance/stable identity | Pass: reuse identity/hash/skip rules | Pass: original timestamps, shared enrichment, ephemeral sequential state |
| III. Test-first | Pass: implementation deferred | Pass: each change starts with observed failing tests; validation below |
| IV. Replaceable boundaries | Pass: use existing interfaces | Pass: pipeline knows only memory interface; composition controls adapters |
| V. Secrets never reach engine | Pass: no engine calls | Pass: sanitizer categories only; no bodies/titles/raw exceptions |

No deviations. ADR-004 stack, single-bank strategy and tag conventions remain intact.
Scope is explicitly Phase 1 item 9 in architecture §22, outside none of §21 exclusions.
Governance impact is none; no decision record amendment is needed.

## Project Structure

Documentation: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`,
`contracts/cli.md`, `checklists/requirements.md`. `tasks.md` is deferred to approval.

Source/test locations:

- `src/engineering_memory/ingestion/pipeline.py`: share preparation, add preview orchestration
  with early return before side effects and no failure-record writes.
- `src/engineering_memory/ingestion/report.py`: immutable preview row/report, separate from actual writes.
- `src/engineering_memory/cli/__init__.py`: expose flag and pass execution mode.
- `src/engineering_memory/cli/runtime.py`: read-only state composition, no memory construction.
- `src/engineering_memory/cli/results.py`: preview envelope and text rendering.
- `tests/unit/`, `tests/integration/`, `tests/contracts/`: synthetic tests at existing boundaries.
- `README.md`, `ARCHITECTURE.md`: document accepted flag and offline preview behavior.

**Structure Decision**: Extend existing modules, no new service, persistence schema or boundary.

## Design and implementation approach

1. Extract shared preparation (sanitize, classify, enrich), retaining real import's early skip.
   Return enriched metadata plus safe redaction categories; never persist preview content.
2. Preview uses shared `may_skip` on original content hash, but prepares skipped rows for metadata.
   A run-local overlay reflects projected imports for repeated identities. Failed preparation
   must not create a successful overlay record; no durable failure recording is allowed.
3. At composition root branch before SQLite initialize and memory factory. Open existing state
   read-only and validate; missing state is empty with no initialization. Replay reads archive
   originals through the existing source. Existing settings validation remains applicable.
4. Preview result uses `dry_run: true` and would-import/would-skip counts and rows. Default
   real-import output remains unchanged. Preserve existing status and exit policy.
5. Test first per change: poison memory construction and all calls; poison archive and state
   writes; test absent paths and snapshots, preparation errors and reader failures. Compare
   preview actions with real runs on identical synthetic input/state, including repeated ids.

## Verification strategy

After approval, observe each targeted test fail before implementing. Then run targeted preview,
ordinary CLI and pipeline tests, `uv run pytest`, `uv run ruff check .` and
`uv run ruff format --check .`. Capture actual outputs in the PR. No live Hindsight is needed
for the preview acceptance tests. Verify text and JSON, both source selectors, force, redaction
canaries, empty sources, missing/corrupt state, recoverable and terminal errors, and interrupts.

## Alternatives considered

- Real import with `--limit`: still writes and incurs extraction cost; does not preview the corpus.
- Independent preview pipeline: duplicates preparation/skip rules and risks decision drift.
- Fake memory adapter alone: runtime would still initialize state and archive data; insufficient.
- Treat preview as imported counts: misleading, and risks confusing predicted with durable outcomes.

## Complexity Tracking

No constitution violations or additional dependencies. One ephemeral state overlay is necessary
for sequential parity; it is discarded and is never a second durable ledger.
