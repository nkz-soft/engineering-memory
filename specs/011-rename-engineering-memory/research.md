# Research: Project Rename

## R1 - Configuration isolation

**Decision**: Use only `ENGINEERING_MEMORY_`, retaining nested delimiter `__` and current environment/file precedence.
**Rationale**: Settings currently centralize the prefix in `ENV_PREFIX`. An old-prefix fallback reintroduces the inherited-environment collision.
**Alternatives considered**: Prefix-only change, compatibility aliases and shorter prefixes. The full project name is clear and directly matches issue #48.

## R2 - Complete identity surfaces

**Decision**: Rename package/import paths, distribution metadata, Hatch package path, uv lock project entry, CLI name/version lookup/output, tracing service/version identity and logging handler marker. Update Docker user creation, ownership and USER together while preserving UID 10001.
**Rationale**: A directory rename alone misses installed runtime metadata and container ownership. Existing structure, CLI, telemetry and image tests provide verification seams.
**Alternatives considered**: A compatibility package or command shim adds maintenance and is not requested for this pre-release project.

## R3 - Documentation and unchanged data

**Decision**: Audit tracked files contextually, including `projects.example.toml` and GitHub issue-template links. Preserve consumer mentions, archive paths, serialized schemas and stable identities. Add a paragraph to ADR-008.
**Rationale**: The rename changes product identity, not persisted conversation semantics. Bulk replacement of Hermes would corrupt genuine consumer descriptions.
**Alternatives considered**: Updating only top-level docs leaves prior specifications and examples inconsistent with the issue's explicit acceptance criteria.

## R4 - Sequencing and external rename

**Decision**: Start from merged ADR-008 at `4ac75a3`; recheck open work before implementation. Perform and verify GitHub repository rename after local changes pass, then create the PR against the canonical URL.
**Rationale**: No open PRs or additional worktrees existed at planning time. GitHub administration and redirect verification are distinct from committing links.
**Alternatives considered**: Renaming the checkout is unnecessary; renaming the repository during planning changes shared infrastructure before design review.

All design unknowns are resolved from the issue and repository. Docker availability and repository administration privileges remain execution checks, not unresolved design choices. Read-only delegated repository research confirmed the additional observability and template-link surfaces.
