# Implementation Plan: Claude Code session history

**Branch**: `026-claude-code-source` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)
**Input**: Issue #27; `specs/026-claude-code-source/spec.md`.

## Summary

Add isolated Claude Code JSONL snapshot and archive readers behind ConversationSource. Preserve
block ordering by emitting normalized messages per text/tool block; encode native association and
error status deterministically in existing ToolActivity request/result strings. Add optional
source repository/cwd fields to Conversation, sanitize them, and compose a metadata classifier
before AliasProjectClassifier. Carry sanitized repository context into per-conversation enrichment.
No tool execution, repository probing or transcript acquisition.

## Technical Context

**Language/Version**: Python 3.13, uv.
**Primary Dependencies**: Existing Pydantic v2 and Typer; standard-library json/path handling.
**Storage**: Existing local raw archive and SQLite import state; no storage schema migration planned.
**Testing**: pytest parser/unit, source contracts, pipeline/CLI integration and opt-in live recall.
**Target Platform**: Windows/Linux CLI and existing Docker product.
**Project Type**: Modular monolith with source adapters.
**Performance Goals**: Read one session at a time; directory enumeration must not load session bodies.
**Constraints**: Synthetic fixtures only; preserve exact originals; fail closed on incomplete JSONL;
no dependency additions or global canonical-hash changes.
**Scale/Scope**: Main-session snapshots; not subagent aggregation, filesystem watching or export capture.

## Constitution Check

| Principle | Before research | After design |
|---|---|---|
| I — Raw archive | Pass: keep exact input bytes | Pass: replay parses originals independently of live checkout |
| II — Provenance/identity | Pass: native session id and times | Pass: deterministic source id/tag, sanitized repository and metadata-first project; unchanged v1 hashes |
| III — Test-first | Pass: planning only | Pass: parser, metadata, sanitizer, contract, integration and recall tests must fail before implementation |
| IV — Replaceable boundaries | Pass: ConversationSource adapter | Pass: classifier chain and generic domain context; no vendor or Hindsight vocabulary in shared stages |
| V — Secrets | Pass: sanitizer precedes retention | Pass: request/result/context fields scanned; no external file reads; synthetic secret checks include access and diagnostics |

All gates pass before and after design. No deviations. Stack, bank, tag meanings and Hindsight
contract unchanged. The source ADR below is required by constitution governance; not a principle amendment.

## Project Structure

### Documentation (this feature)

`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/source.md`, `quickstart.md`,
`checklists/requirements.md`. Generate `tasks.md` only after the human gate.

### Source Code (repository root)

- `src/engineering_memory/ingestion/claude_code/`: source, parser, archive reader and package exports.
- `src/engineering_memory/normalization/conversation.py`: optional `repository`, `working_directory`.
- `src/engineering_memory/sanitization/pattern_sanitizer.py`: scan context fields and coverage registry.
- `src/engineering_memory/classification/`: explicit metadata classifier using existing chain/rules.
- `src/engineering_memory/ingestion/pipeline.py`: per-conversation sanitized repository enrichment.
- `src/engineering_memory/cli/`: explicit selector, reader registration and classifier composition.
- `tests/unit/`, `tests/contracts/`, `tests/integration/`, `tests/synthetic/`: synthetic session checks.
- `ARCHITECTURE.md`, operator documentation: accepted ADR and supported dialect/use instructions.

**Structure Decision**: Extend the generic conversation context rather than passing vendor metadata
through side channels. ToolActivity already contains scanned request/result strings; no new tool
fields or global canonical version needed. One normalized message per block preserves mixed order.
Validate older normalized archive loads with missing optional context and existing hashes.

## Delivery and Verification Design

1. Fail parser tests on synthetic JSONL covering text, paired/parallel tools, diffs, unfinished and
   orphan calls, unknown blocks, metadata events, missing ids/time, duplicates and incomplete input.
   Implement a resumable source iterator: each failed file advances before raising SourceFormatError.
2. Fail then pass optional context model/round-trip and sanitizer coverage tests. Prove legacy
   ChatGPT/Claude chat canonical bytes stay unchanged; changed tool output changes the session hash.
3. Fail metadata classifier tests for Windows/POSIX/URL contexts, explicit-context versus prose
   conflict, alias mapping, invalid slug fallback and unknown context. Compose ahead of aliases.
4. Fail pipeline provenance tests: sanitized per-session repository takes priority over the existing
   run-wide repository fallback. Preserve old behavior when conversation context is absent.
5. Fail source contracts (CS-1–CS-7), archive replay, force, dry-run, unchanged skip and changed-output
   update tests. Corrupt one file in a batch and prove the following session still imports.
6. Fail CLI selection/registration tests then add the adapter; verify existing default and source
   refusal remain compatible. Update docs and append the ADR with the next available number.
7. Exercise import/recall/access with a synthetic failure-investigation-fix session and known project;
   verify actual Hindsight source/project filters and document identity through an opt-in live test.
   Missing live configuration is explicitly unverified, never counted as a passing integration gate.
8. Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`, plus the documented
   opt-in live scenario; record actual outcomes, review code and only then open a templated PR.

## Decision Record — Proposed ADR-010: Claude Code session source

**Status**: Proposed for human review. Append to ARCHITECTURE.md during implementation after checking
number availability; ADR-007 remains reserved, ADR-009 is Claude plain chat.
**Context**: Issue #27 requires command/error/investigation/solution preservation and first use of
§15 explicit project metadata. Existing ToolActivity represents request/result text, while
Conversation lacks source repository context. Vendor API tool semantics are documented; local
session-envelope compatibility is bounded by the fixture dialect, not claimed as a stable vendor API.
**Decision**: Parse operator-provided JSONL main-session snapshots in a dedicated source, archive exact
bytes, preserve block order and tool association in deterministic request/result text, and add generic
optional repository/cwd context. Sanitize every new textual field, compose metadata classification
before alias matching, and enrich each session using its own repository. Replay reparses originals.
Canonical v1 coverage stays unchanged; context-only corrections require force/replay to refresh memory.
**Alternatives considered**: Prose-only import loses the issue's evidence. A parallel pipeline duplicates
policy. Live repository inspection breaks portable replay. Inferring projects from tool arguments
confuses mentioned paths with source context. Structured tool fields require a canonical migration
without a present consumer benefit; retain native association in deterministic existing strings.
**Consequences**: No new dependency or global re-extraction. The supported local dialect is explicitly
limited; externalized output files and subagent aggregation need separate design. New context fields
require sanitizer/serialization coverage, and basename-derived projects can collide until aliases map them.

## Complexity Tracking

No constitution violations or exceptions.
