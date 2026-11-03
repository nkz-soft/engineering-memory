# Implementation Plan: Shared memory for coding agents

**Branch**: `028-coding-agent-access` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)
**Input**: Issue #29 under ADR-008 and constitution v1.3.0.

## Summary

Connect Claude Code and Codex through supported stdio MCP configuration to the existing
`engineering-memory serve` command. Document clean-client recipes and demonstrate
ChatGPT-to-Claude Code and imported-Claude-Code-to-Codex visibility using synthetic history.
Reuse the existing imports, tools and shared bank; no production API change is planned.

## Technical Context

**Language/Version**: Python 3.13, uv; Markdown configuration guides.
**Primary Dependencies**: Existing MCP SDK 2.3.0, Typer, source adapters and client MCP
support. No new runtime dependency planned.
**Storage**: Existing local archive, SQLite import state and self-hosted Hindsight behind
MemoryStore; `engineering-global` for operator acceptance.
**Testing**: pytest, SDK stdio integration, isolated backend gate and two live clients.
**Target Platform**: Local client processes; absolute executable/archive paths, including Windows.
**Project Type**: Existing modular monolith CLI; consumer documentation/validation slice.
**Performance Goals**: Existing search/page bounds; no new latency SLA.
**Constraints**: Read-only access, no direct engine integration or network listener;
synthetic evidence only. Skips are not acceptance.
**Scale/Scope**: Two clients, two Phase 2 journeys, one corpus with project/source filtering.

## Constitution Check

Pre-research and post-design: PASS, no deviations.

- **I — Archive**: Decisions/refinements enter through importers with original and normalized
  archival. No tool writes memory; consumers read sanitized normalized context only.
- **II — Provenance**: Verify source-native identities, real timestamps, tags and unchanged
  import skipping; no identity or tag convention change.
- **III — Test-first**: For each executable change, write a behavioral test and observe failure
  before implementation. Validate documentation by executing recipes; record actual client
  evidence separately from automated tests.
- **IV — Boundaries**: Clients connect only to `serve`. Existing MemoryAccess/interfaces
  remain the boundary; backend construction remains at the CLI composition root.
- **V — Secrets**: Local stdio, environment-based credentials, synthetic fixtures, sanitized
  output and safe errors. No original bytes or personal configuration in public evidence.
- **Stack/bank/governance**: Existing stack and bank retained. ADR-008 already resolves the
  issue's obsolete integration wording; no new decision record or amendment is needed.

## Project Structure

### Documentation (this feature)

`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/consumer-validation.md`,
`quickstart.md`, `checklists/requirements.md`. Defer `tasks.md` until human approval.

### Source Code (repository root)

- `docs/operations/coding-agent-memory.md`: proposed shared setup, two client recipes,
  queries, troubleshooting, acceptance procedure and official references.
- `docs/claude-code.md`, `docs/codex.md`, `README.md`: link import and read workflows.
- `tests/integration/test_coding_agent_access.py`: proposed synthetic cross-source
  import-to-stdio regression reusing fixture builders and import helpers.
- `deploy/hindsight/e2e.py`: wire regression into the isolated live worker if extending
  that gate; preserve bounded runtime, isolation and missing/skip rejection.
- `specs/028-coding-agent-access/verification.md`: actual implementation evidence/blockers.
- Existing access, CLI and parsers are reused; runtime changes require a demonstrated
  failing acceptance behavior within scope.

**Structure Decision**: Consumer onboarding and verification, not another engine adapter.

## Design and Verification Sequence

1. Verify installed client versions against the official sources in research.md. Use explicit
   paths and test environment forwarding, especially Codex's `env_vars` allow-list.
2. Prepare synthetic ChatGPT decision, other-project competitor and supported Claude Code
   refinement snapshots. Keep expected answers outside retrieval prompts. Automated fixtures
   are not evidence that a real client authored a session.
3. Test-first add import-to-stdio coverage for project/source filtering, stable identity,
   original time, before/after import visibility, archive paging and unchanged-import skipping.
   Reuse isolated backend/extraction fixtures; mocks alone cannot establish live semantics.
4. Write operations guide with complete server settings, safe credential forwarding,
   client registration, discovery, fresh-session use and local removal/restart instructions.
5. Run targeted tests, full pytest, `uv run ruff check .`, `uv run ruff format --check .`
   and isolated live gate with no required-test skips.
6. Against a prepared local operator corpus using `engineering-global`, demonstrate Claude
   Code recall, create a synthetic refinement in that session, take a quiescent snapshot,
   dry-run/import it, then retrieve in fresh Codex. Unsupported actual dialects are blockers,
   not permission to expand parsers or silently rewrite a transcript.
7. Record versions, revision, exact safe commands, actual tool calls/results and separate
   journey statuses. Review before PR; live acceptance stays open if a client is unavailable.

## Alternatives and Risks

- Default per-repository banks: rejected by ADR-002; fragments shared history.
- Native Hindsight integrations: rejected by ADR-008 and Principle IV; bypass archive context.
- Tool writes: rejected by Principles I/IV; refinements enter through imported sessions.
- SDK-only proof: useful regression coverage but insufficient for issue acceptance.
- Automatic capture, dialect expansion and new tools: separate features.
- Client version/permission drift: record tested versions and actual tool discovery/calls.
- Missing backend, credentials or supported snapshot: record a blocker, never substitute a
  passing mock result. Existing prerequisite issue closure does not prove current live readiness.
- Client cwd/environment differences: explicit paths and nonsecret forwarding examples are
  part of recipe validation. Tags scope results, not access permissions.

## Complexity Tracking

No constitution violations, new schema, boundary, source adapter or architectural decision.
