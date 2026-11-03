# Implementation Plan: Codex session source

**Branch**: `027-codex-session-source` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)
**Input**: Issue #28, specs/027-codex-session-source/spec.md

## Summary

Add a dedicated Codex JSONL adapter, registered with the existing CLI and original-archive replay dispatch. Reuse generic cwd/repository context from #27, the shared pipeline and existing ToolActivity strings. Limit compatibility to a documented, synthetic-fixture-backed dialect.

## Technical Context

**Language/Version**: Python 3.13.
**Primary Dependencies**: Existing Pydantic v2, Typer, structlog and standard JSON/path handling; no new dependencies.
**Storage**: Existing local raw archive, SQLite import state, shared engineering-global bank.
**Testing**: pytest unit/source contracts/pipeline/CLI/replay tests; opt-in live Hindsight recall.
**Target Platform**: Existing local CLI runtime with Windows and POSIX snapshot paths.
**Project Type**: Modular monolith/CLI.
**Performance Goals**: Iterate one snapshot at a time; no entire-corpus materialization.
**Constraints**: No private session contents in committed fixtures; no live source acquisition; no engine-specific code outside memory/hindsight.
**Scale/Scope**: One normalized conversation per saved session; selected file or flat directory.

## Constitution Check

Pre-research and post-design: PASS, with no deviations.

1. Raw archive: preserve exact snapshot bytes and sanitized normalized form; replay dispatch reparses original bytes.
2. Provenance/identity: existing Source.CODEX, codex:{native-id}, real source dates, importer version, source/project tags and shared hash/upsert policy.
3. Test-first: implementation must demonstrate failing tests before parser/registration changes; source contracts and live recall acceptance remain gates.
4. Replaceable boundaries: implement ConversationSource; reuse classifier/pipeline/store interfaces. No direct Hindsight dependency in adapter or CLI.
5. Secrets: existing sanitizer covers dialogue, serialized tool payloads and context; regressions include multiline and nested JSON secrets. Access serves sanitized content only.

## Project Structure

Documentation: spec.md, plan.md, research.md, data-model.md, contracts/source.md, quickstart.md, checklists/requirements.md in this directory. tasks.md is deferred until approval.

Planned source changes: src/engineering_memory/ingestion/codex/{__init__,parser,source,archive_source}.py; existing CLI source registry and original-archive replay dispatch; README.md and ARCHITECTURE.md.
Planned validation: tests/unit, tests/contracts/test_codex_source.py, tests/integration, synthetic fixtures under tests only.

**Structure Decision**: Follow the Claude Code adapter pattern while keeping independent format parsing and unchanged shared domain contracts.

## Implementation Sequence (after approval)

1. Write failing synthetic parser cases: native id/time, ordered text, function/custom tool requests and outputs, unfinished/orphan calls, duplicate event mirrors, metadata-only files and unknown records. Implement bounded dialect and deterministic tool text.
2. Prove resumable source contract CS-1–CS-7, file errors, empty input, duplicate native ids, symlinks and stable original bytes.
3. Prove sanitizer/context classification, unchanged canonical behavior for other sources, and tool-output changes affecting content hashes. Reuse metadata classifier without new source-specific policy.
4. Add failing CLI registration and archive replay cases before integrating Codex. Prove dry-run, unchanged skip, changed update and force through the shared pipeline.
5. Append the separate ADR and document supported fields, exclusions and operator commands.
6. Run formatting/lint and full pytest, then opt-in live recall filtered by source/project. Explicitly report live checks as unverified if service configuration is absent.

## Decision Record — Proposed ADR-011: Codex session source

**Status**: Proposed; verify next available ADR number during implementation.
**Context**: §2 and issue #28 require Codex sessions in the shared bank, independently specified from Claude Code.
**Decision**: Parse saved Codex JSONL through a dedicated adapter, select response items as the dialogue authority, retain exact originals, normalize tool evidence into existing generic fields, and use session metadata cwd for level-1 classification. Reuse the established pipeline and replay path.
**Alternatives considered**: One Claude Code/Codex parser conflates independently evolving formats. Event-only ingestion loses structured tool evidence and can duplicate response items. Live Codex APIs/acquisition expands scope and undermines portable archive replay. A new normalized schema/hash version is unnecessary for this bounded source.
**Consequences**: Explicit format limits and synthetic compatibility tests are maintained. No new storage, bank, dependency or consumer-facing engine configuration. Future event-only dialects and subagent reconstruction need separate design.

## Complexity Tracking

No constitution violations. Risks: upstream format drift, duplicate event streams, compaction replay, orphan tool records and ambiguous context. The source contract specifies deterministic handling; implementation must expand fixtures before claiming additional dialect support.

