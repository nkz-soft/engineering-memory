# Implementation Plan: Project mental models

**Branch**: `029-project-mental-models` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Issue #30; Phase 3 wave 1, depends on #25, enables #31.

## Summary

Manage three standing project summaries in the existing Hindsight bank. Add separate
engine-neutral read and maintenance capabilities, an importer-side operator refresh command,
and a read-only MCP retrieval tool. Refresh explicitly after import, never on consumer reads.
Keep summaries disposable and ground their references in sanitized archived conversations.
Stop at planning review: no implementation or tasks.md before approval.

## Technical Context

**Language/Version**: Python 3.13, uv.
**Primary Dependencies**: Existing httpx, Pydantic v2, Typer and MCP SDK; pinned Hindsight
1.1.0. No new runtime dependency or backend upgrade planned.
**Storage**: Existing local archive, SQLite import state and shared `engineering-global`
bank; derived summaries in the backend, no new authoritative store or import-state schema.
**Testing**: pytest unit/contracts/stdio integration; isolated pinned-engine lifecycle gate;
separate real-extractor semantic acceptance with synthetic conversations.
**Target Platform**: Existing local CLI/container deployment and stdio clients.
**Project Type**: Modular monolith plus external self-hosted engine.
**Performance Goals**: Bounded read of one model, no synthesis during reads. Default finite
240-second refresh deadline per kind, bounded HTTP retries and polling; 2048-token summaries.
**Constraints**: Strict project inputs, safe errors, environment credentials, archive grounding,
read-only consumers; no scheduler, worker, arbitrary model editor or general reflection.
**Scale/Scope**: Three fixed kinds per explicitly selected project; independent per-kind outcomes.

## Constitution Check

Pre-research and post-design: PASS, no principle deviations. Source research is not evidence
that the running backend passes; live verification remains an implementation gate.

- **I — Archive**: Models derive only from successfully imported sanitized history, remain
  disposable, and are never re-retained as original conversations. Importer-side maintenance
  creates derived artifacts; consumers cannot author memory or alter the archive.
- **II — Provenance**: Existing document IDs, original times and tags remain. Model identity
  is project/kind, with its own refresh time and multiple verifiable supporting documents;
  never fabricate a single conversation provenance for a synthesized answer.
- **III — Test-first**: Observe failing behavioral tests before implementing each executable
  change. Cover new boundaries, adapter, CLI, MCP and import-to-refresh-to-read. Required live
  cases must run without skips; a successful operation alone does not prove answer quality.
- **IV — Boundaries**: Add `ProjectModelReader` and `ProjectModelMaintainer` in memory/interface;
  implement engine mechanics only in memory/hindsight. Access receives the reader only.
  Importer-side orchestration uses the maintainer; CLI only assembles dependencies. Existing
  MemoryStore retain/recall callers need no new methods.
- **V — Secrets**: Sanitization precedes retention; models use those facts only. Environment
  credentials, local stdio, sanitized support reads, fixed safe errors and content-free logging.
  Generated text/history remain untrusted evidence, never executable instructions.
- **Stack/bank/governance**: Existing stack, shared bank and project tags retained. This
  extends the Hindsight contract, despite the issue's “None” governance tick. Record the
  decision below as ADR-012 (recheck numbering at implementation), updating architecture
  §§9,16,22. No constitutional amendment: no consumer writes or new history source.

### Decision record — Importer-side derived project models

**Decision**: Three fixed definitions, stable project/kind identities, strict source tags,
explicit post-import refresh, separate neutral read/maintenance capabilities and read-only
consumer retrieval. Disable automatic consolidation refresh for managed definitions and use
full refresh initially. Any incompatible existing definition is rejected rather than adopted.

**Rationale**: Delivers Phase 3 while preserving replaceability, one shared bank and the
archive-backed access surface (ADR-001, ADR-002, ADR-008).

**Consequences**: Operators refresh affected projects after imports. Refresh failure never
changes conversation import success. Refresh time is not a corpus watermark; expose stale
and failure metadata separately. Citation resolution and lifecycle join the live engine contract.

## Project Structure

### Documentation (this feature)

`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/project-models.md`,
`quickstart.md`, `checklists/requirements.md`. Defer tasks.md until human approval.

### Source Code (repository root)

- `src/engineering_memory/memory/interface/project_models.py`: proposed types/protocols.
- `src/engineering_memory/memory/hindsight/project_models.py`: proposed definitions, identity,
  lifecycle HTTP, bounded polling, private citation normalization.
- `src/engineering_memory/ingestion/project_models.py`: proposed neutral maintenance orchestration.
- `src/engineering_memory/cli/`: compose dependencies; add `models refresh` command.
- `src/engineering_memory/access/{service,server}.py`: read-only `get_project_model` tool.
- `tests/unit/`, `tests/contracts/`, `tests/integration/`: behavioral model/adapter/CLI/MCP tests.
- `deploy/hindsight/`: extend isolated live gate with mandatory model cases and skip rejection.
- `docs/operations/project-models.md`, consumer guides, `README.md`, `ARCHITECTURE.md`:
  operator sequence, client reads, limits and decision record.
- Feature `verification.md`: actual commands/evidence during implementation.

**Structure Decision**: Separate optional capabilities keep existing retain/recall contracts
small and prevent write capability from crossing into consumer access.

## Design and Verification Sequence

1. Test-first define project/kind validation, stable identity, result/failure types and narrow
   protocols. Reject blank/unclassified projects; preserve exact established project values.
2. Verify pinned API against an isolated bank: create/get/refresh, strict tags including
   untagged exclusion, asynchronous completion, repeated setup and failure metadata.
3. Implement three fixed questions: architecture/components; current technologies with explicit
   supersession; settled decisions/rationale versus proposals. Require gaps/conflicts and
   supports; never embed expected acceptance answers. Backend IDs use SHA-256 over canonical
   project/kind, independent of generated content; tags contain only the existing project tag.
4. Normalize supporting fact/observation references to imported document provenance inside
   the adapter. Reader service validates project and sanitized archive identity. Unresolvable
   provenance fails closed; no invented citations or conversion to a one-conversation RecallResult.
5. Add importer-side `models refresh --project <value> [--kind <kind>] --json`: ensure compatible
   definitions, refresh, wait to deadline and report independent outcomes. Reconcile existing
   IDs/operations after ambiguous submission; never blindly repeat side-effecting POSTs.
6. Add read-only `get_project_model` with strict schema, safe errors, missing/pending outcomes,
   stale/failure metadata, supports and read-only annotations. Reads never create/refresh.
7. Document import → refresh → next consumer read, unchanged imports, stale summaries,
   partial failures and recovery. Update architecture with the decision above.
8. Run targeted tests, full `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`
   and extended isolated live gate. Fixture LLM tests prove wire/lifecycle behavior; a real
   configured extractor separately proves coherent grounded synthesis after new imports.
9. Demonstrate two complementary alpha conversations, beta and untagged decoys, superseding
   decision, repeated refresh, sparse/conflicting evidence and last-good preservation on failure.
   Record versions/revision/safe commands/outcomes using synthetic history only; review and fix
   findings before the PR. Missing runtime/LLM or unverified supports blocks acceptance.

## Alternatives and Risks

- Issue alternative, reconstruct with recall each time: slow and inconsistent standing picture.
- General reflect on each read: hidden generation lifecycle; belongs to #31.
- Per-project banks/direct engine consumers: contradict ADR-002/ADR-008.
- Automatic refresh per import/consolidation: unnecessary coupling and unclear failure ownership;
  explicit refresh is the documented first version, with no automatic freshness promise.
- Archiving/re-retaining summaries as conversations: circular evidence and false source authority.
- Stable IDs prevent duplicates, not concurrent writes. Detect/reconcile pending operations and
  report bounded uncertainty; no cross-process locking claim.
- Pinned source exposes citation and freshness fields, but their runtime shape and resolvability
  must pass live tests. If unsupported, stop acceptance rather than weaken grounding or silently
  upgrade the engine. Explicitly distinguish operation completion from supported synthesis.

## Complexity Tracking

No principle deviation, new service, queue, source or import-state schema. Separate reader and
maintainer capabilities are justified by the read-only access rule and replaceable boundaries.
