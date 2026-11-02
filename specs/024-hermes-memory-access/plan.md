# Implementation Plan: Hermes memory access

**Branch**: `024-hermes-memory-access` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)
**Input**: Issue #25 interpreted under ADR-008 and constitution vCurrent.

## Summary

Provide the first read-only stdio MCP access surface, wire it at the CLI composition
root, and document connecting Hermes to it. Prove imported ChatGPT history is visible
in a fresh Hermes conversation with source provenance. ADR-008 supersedes the issue's
native Hindsight provider wording; no governance change is proposed.

## Technical Context

**Language/Version**: Python 3.13, uv.
**Primary Dependencies**: Existing Typer, Pydantic and boundaries; add official `mcp`
SDK, select and lock its stable compatible release during implementation.
**Storage**: Existing local normalized archive; existing self-hosted memory backend
and `engineering-global` bank behind MemoryStore. No new storage or schema.
**Testing**: pytest unit/contract tests, SDK stdio client integration, existing live
import fixture, and manual fresh Hermes conversation.
**Target Platform**: Local process launched by Hermes; explicit absolute paths support
launching from a consumer directory. No network listener.
**Project Type**: Modular monolith CLI plus consumer-facing MCP tools.
**Performance Goals**: Bounded output: search defaults to 10, maximum 100 results;
conversation pages default to 50, maximum 100 messages. No latency SLA asserted.
**Constraints**: Only two read tools; stdout reserved for protocol, diagnostics stderr;
secrets from environment; normalized archive only; no importer or extractor startup.
**Scale/Scope**: One shared bank, one local archive; first Hermes consumer only.

## Constitution Check

Pre-research and post-design gates: PASS, no deviations.

- I: No writes; facts continue to originate in archived imports. Conversation reads
  use RawArchive.load and never load_original.
- II: Derive document_id deterministically from source/source_id; retain all returned
  provenance and enrich original time from normalized archive started_at.
- III: Write failing unit/contract tests before each implementation change, observe
  red, implement and rerun. Verify the live consumer separately from test doubles.
- IV: Access receives MemoryStore/RawArchive interfaces. Concrete adapters live in
  the CLI composition root. Consumers only see engineering-memory tool contracts.
- V: No port; sanitized normalized messages only; safe errors omit exception chains,
  credentials, paths and content. No logs of requests or returned history.
- Stack/bank: Official MCP Python SDK already authorized by ADR-008; no substitute
  framework, per-consumer bank or tag-convention change.

## Project Structure

### Documentation (this feature)

`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/tools.md`,
`quickstart.md`, `checklists/requirements.md`; tasks.md is deferred to Phase 2.

### Source Code (repository root)

- `src/engineering_memory/access/`: validated request/result models, interface-injected
  read service and MCP registration. No concrete backend imports.
- `src/engineering_memory/cli/`: proposed `serve` command and runtime composition,
  cleanup on disconnect and signals. Server startup does not provision banks or import.
- `src/engineering_memory/settings.py`: access-specific configuration loader using
  ENGINEERING_MEMORY_ and existing path semantics, without extraction LLM requirements.
- `pyproject.toml`, `uv.lock`: official SDK dependency.
- `tests/unit/`, `tests/contract/`, `tests/integration/`, `tests/structure/`:
  add tests in the repository's existing layout for access behavior, protocol and boundaries.
- `docs/operations/hermes-memory.md`: reproducible consumer configuration and evidence
  procedure, linked from README.md. No user configuration files are changed automatically.

**Structure Decision**: Extend the existing access placeholder; keep adapter construction
outside access. Import-state has no role in these initial tools; defer listing/reflect.

## Design and Verification Sequence

1. Test-first request validation, error mapping, provenance mapping and archive paging.
2. Test-first tool registration and stdio lifecycle with official SDK client; assert
   exactly two tools, no write method and no protocol contamination.
3. Test-first CLI composition/settings; missing extraction credentials do not prevent
   reads, missing backend credentials fail safely, unrelated cwd resolves explicit paths.
4. Run existing regression suite, lint and format checks. Confirm access has no backend
   implementation imports. Use synthetic secret sentinels to prove original bytes never leak.
5. Import the synthetic acceptance conversation using the existing workflow, then
   exercise both tools against the live deployment. Verify scoped distractor exclusion.
6. Connect Hermes, record version and fresh-session tool discovery, ask the blind fact
   question, follow document_id to the normalized messages. Record only safe synthetic
   evidence. Report unavailable prerequisites as blocked acceptance, not a passing check.

## Alternatives and Risks

- Native Hermes provider/direct Hindsight MCP: rejected by ADR-008 and Principle IV.
- Stop at importer E2E (#23): rejected because it does not exercise Hermes.
- Implement reflect/listing or selectable engine matching modes now: deferred; no
  consumer requirement justifies new boundary methods.
- Missing archive behind a recalled fact: fail the search safely with archive-not-found,
  do not silently substitute import time or omit required provenance.
- Message-count paging bounds count rather than bytes; one oversized message can still
  be large. Document this limitation; do not silently truncate source text.
- Hermes and SDK versions evolve: lock the SDK and record tested Hermes version at
  implementation, verify published configuration against that actual installation.

## Complexity Tracking

No constitution violations or new architectural decision required.
