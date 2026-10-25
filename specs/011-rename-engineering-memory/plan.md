# Implementation Plan: Rename to Engineering Memory

**Branch**: `011-rename-engineering-memory` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)
**Input**: Issue #48 and the feature specification in this directory.

## Summary

Adopt `engineering-memory` / `engineering_memory` consistently and replace the shared configuration prefix with `ENGINEERING_MEMORY_`. Preserve Hermes as a consumer and preserve all stored-data contracts. Extend ADR-008 with the rename rationale. The repository rename is a separately verified external step after implementation checks; do not imply it was performed merely by editing links.

## Technical Context

**Language/Version**: Python 3.13.
**Primary Dependencies**: Existing Pydantic v2, pydantic-settings, Typer, structlog and OpenTelemetry; no new dependencies.
**Storage**: Existing archive and import-state contracts; no storage migration.
**Testing**: pytest, Ruff, installed CLI smoke checks and existing Docker/CI checks.
**Target Platform**: Existing development environments and Linux container.
**Project Type**: Python package and CLI modular monolith.
**Performance Goals**: No new performance behavior; preserve current behavior.
**Constraints**: Test-first; no old-prefix fallback; sanitized diagnostics; no private data in fixtures; keep UID 10001.
**Scale/Scope**: All tracked identifier references, examples, prior specs, CI, lock metadata and one GitHub repository setting.

## Constitution Check

Pre-research and post-design checks both PASS:

- **I / Raw archive**: No change to persistence ordering, original/normalized forms, archive paths or replay behavior.
- **II / Provenance and identity**: Preserve document IDs, content hashes, timestamps, tags, importer behavior and `engineering-global` bank identity. Rename service/package identifiers only.
- **III / Test-first**: First add isolated settings regressions and observe failures against the current prefix; then change settings. Update packaging/CLI/container identity expectations and observe failures before renaming those implementations. Record red and green commands in implementation verification.
- **IV / Replaceable boundaries**: Rename module paths without changing interfaces or introducing Hindsight references outside its adapter; no MCP implementation is added by this rename.
- **V / Secrets**: Dedicated configuration prefix prevents inherited consumer values from being consumed. Preserve safe errors, secret masking, normalized-only access and local transport constraints.
- **Stack / Governance**: No dependency or principle changes. Update project wording in the constitution and explain the rename in ADR-008; no separate ADR or semantic governance amendment is needed.

## Project Structure

### Documentation (this feature)

`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/identity.md`, `quickstart.md`, `checklists/requirements.md`. `tasks.md` is generated only after the human gate.

### Source Code (repository root)

- Rename `src/hermes_memory/` to `src/engineering_memory/`, preserving its boundary layout.
- Update source/test imports and identity literals in CLI, version lookups, tracing and logging internals.
- Update `pyproject.toml`, regenerate project metadata in `uv.lock`, and update `.env.example`.
- Update Docker user/ownership/entrypoint, CI image tags and corresponding structure tests.
- Update README, architecture, CLAUDE, constitution, docs, prior specs, project examples and GitHub template links.

**Structure Decision**: Preserve the existing src-layout modular monolith. No additional modules, compatibility shims or dependencies.

## Implementation Sequence After Approval

1. Generate tasks from this design. Verify branch is based on current `origin/main` and check for newly opened conflicting work before implementation.
2. Add new-prefix and inherited-consumer regression tests using synthetic values, explicit environment isolation and controlled environment files. Observe failure before changing configuration code.
3. Change the prefix and update existing configuration tests/examples, preserving nested delimiter, defaults and precedence.
4. Change identity test expectations, observe failure, then rename package/imports, project/lock metadata, console script, version lookups, observability identities, Docker user/ownership and CI tags together.
5. Update project-name prose and links contextually; preserve Hermes consumer references and former-prefix negative-test inputs. Add the ADR-008 paragraph and migration instructions. Never replace the bare word Hermes globally.
6. Run the full tests, Ruff checks, locked installation, packaged CLI and container smoke checks. Audit tracked identifiers and explain any remaining old strings. Review the finished diff against the constitution and this plan.
7. Rename the GitHub repository using authenticated repository administration, verify the redirect and new URL, and update the worktree remote to the canonical URL. If permissions prevent it, report the blocker and leave that acceptance item incomplete.
8. Create the pull request using the repository template, reference `Closes #48`, attach it to this chat, and move the issue to `in-review`. Leave the worktree available for review.

## Alternatives Considered

- Change only the prefix: fixes the collision but leaves the misleading project identity and documentation mismatch.
- A shorter name such as lore or recall: diverges from the architecture's existing name with no stated benefit.
- Retain aliases for the old prefix: rejected because it preserves consumer configuration collision. No import/CLI compatibility aliases are required.

## Validation and Completion Evidence

Follow [quickstart.md](quickstart.md). Record command output, including failures before implementation. Local Docker availability and GitHub administration are checked during implementation; unavailable checks remain explicitly incomplete and CI is used for image evidence when available. A baseline pytest run is recorded in the Phase 1 issue comment, not represented as verification of the future rename.

## Complexity Tracking

No constitution violations or additional architectural complexity.
