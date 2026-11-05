# Feature Specification: Refresh deployment and development dependencies

**Feature Branch** `030-refresh-dependencies`
**Created** 2026-11-05
**Status** Draft
**Input** [GitHub issue #73](https://github.com/nkz-soft/engineering-memory/issues/73)

## User Scenarios & Testing

### User Story 1 - Upgrade local memory services (Priority: P1)

An operator can start the requested memory and proxy releases on a clean deployment or upgrade a disposable copy of an existing deployment and continue to recall its memories.

**Independent Test** Exercise the standalone and product Compose paths with isolated state and verify health and a retain/recall round trip through the configured proxy.

1. **Given** a fresh stack, **when** the operator starts it and retains a synthetic fact, **then** the services become healthy and the fact is recalled.
2. **Given** a disposable copy with a known retained fact, **when** the operator upgrades it, **then** the fact is still retrievable and newly retained facts can be recalled.

### User Story 2 - Preserve the issue workflow (Priority: P2)

A maintainer can use the updated specification tooling with the project's existing workflow on PowerShell and Claude.

**Independent Test** Generate a scratch feature from the migrated setup, inspect its generated files and rerun task-to-issue mapping against the same fixture.

1. **Given** the migrated assets, **when** a maintainer starts a scratch feature, **then** the next sequential number, matching branch and feature directory, and expected PowerShell and Claude workflow are available.
2. **Given** an existing issue with a generated task identifier, **when** the same task is mapped again, **then** the existing issue is recognized and no duplicate is created.

### User Story 3 - Verify builds and dependency resolution (Priority: P2)

A maintainer can verify that a clean environment and the built application use the intended versions and that CI still catches a synthetic secret.

**Independent Test** Run locked installation, lint, formatting, tests, image build and smoke checks, and the history scan with its negative control.

1. **Given** a clean checkout, **when** the checks and image build run, **then** they succeed and report the resolved runtime and dependency manager versions.
2. **Given** a synthetic finding, **when** the scanner runs its negative control, **then** it reports a finding with the expected failure status.

### Edge Cases

- A target image manifest may lack one of the required Linux architectures.
- Existing data may require a documented migration step before it can be opened.
- A candidate dependency may be incompatible with the existing stack or supported runtime.
- Regeneration may overwrite project customizations or generate an already used feature number.

## Requirements

- **FR-001** Use the exact Hindsight and LiteLLM releases and digests in issue #73 and verify Linux amd64 and arm64 manifest support.
- **FR-002** Verify clean startup, existing-data upgrade and health and retain/recall through the configured proxy, covering both Compose paths.
- **FR-003** Update the Specify CLI and tracked assets to the requested release while preserving the constitution, existing specs, local customizations, sequential numbering, Claude skills and PowerShell support.
- **FR-004** Review the CI action major upgrades and runner requirements, retain full history for secret scanning, and prove the synthetic finding still fails the scan.
- **FR-005** Keep Python 3.13 and verify the resolved Python patch and uv version in CI and the application image build.
- **FR-006** Refresh compatible Python dependencies, keep installation locked, and record each candidate held back with a concrete compatibility reason.

## Success Criteria

- **SC-001** Both image manifests cover both required architectures. Both deployment paths pass their applicable health and retain/recall checks, with an existing fact recovered after the disposable upgrade.
- **SC-002** A scratch feature completes the workflow checks with the expected sequential identifier, and mapping the same task twice yields one issue identity.
- **SC-003** Locked sync, lint, formatting, tests, and image build and smoke checks pass. The secret scan sees full history and its negative control reports a finding.
- **SC-004** Review evidence names the actual Python and uv versions, the dependency changes and any compatibility holdbacks.

## Assumptions

- The audit and acceptance criteria define an in-scope maintenance change under Architecture §21–22. The scope involves the existing stack and needs no governance amendment.
- Upgrade validation may use a disposable copy of state seeded under the old release with synthetic content. Issue #71 tracks related live-agent validation separately.
- The audited Python and uv versions are targets subject to availability and compatibility. Any exception requires concrete evidence.
