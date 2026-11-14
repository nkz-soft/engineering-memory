# Feature Specification: Workstation Installers

**Feature Branch**: `035-workstation-installers`
**Created**: 2026-11-14
**Status**: Draft
**Input**: [Issue #91](https://github.com/nkz-soft/engineering-memory/issues/91)

## User Scenarios & Testing

### User Story 1 - Install and verify the CLI (P1)

A workstation user downloads the package for their operating system, checks its
SHA-256 against the published value, installs it, and runs
`engineering-memory --version` from a new terminal.

**Independent test**: On clean Windows x64 and supported Linux x86_64, each
published installer installs the CLI without a checkout, Python or uv. The
installed version is `0.1.0` for tag `v0.1.0`.

### User Story 2 - Set up memory and retrieve its source (P1)

An operator follows the first-run instructions to check prerequisites, configure
a supported LLM provider privately, select durable storage paths, start Hindsight,
provision the shared bank, and import a synthetic ChatGPT export. A fresh Codex
or Claude Code session finds a known decision and opens its source conversation
through the installed local MCP command.

**Independent test**: Complete this sequence on each supported platform using
the same installed binary from both the terminal and an agent launched
independently. Use an invented decision whose answer is absent from the prompt.

### User Story 3 - Keep memory through restart and reinstall (P1)

An operator stops and starts the stack, reinstalls the same release, and
continues using the same configuration, archive, SQLite state and Hindsight data.

**Independent test**: After each operation, inspect status, retrieve the same
decision and source from a new agent session, and re-import the unchanged
fixture to confirm it is skipped. Verify that the original archive is intact.

### User Story 4 - Rebuild and publish a versioned release (P2)

A maintainer builds the two packages from the tagged source and publishes the
verified installers, their SHA-256 checksums, release notes, and platform steps.

**Independent test**: Rebuild from the release tag on both build platforms,
verify version and asset names, and validate the GitHub Release downloads
against the attached checksums.

### Edge Cases

- Missing Docker, a stopped daemon, unsupported Compose, or a busy port produces
  an actionable failure before the operator proceeds to provisioning.
- Paths with spaces and a different launch directory work for CLI and MCP.
- An absent provider key or an invalid configuration produces a diagnostic
  without printing secret values or opening an MCP listener.
- A failed startup, repeated setup, or reinstall leaves existing state available.

## Requirements

### Functional Requirements

- **FR-001**: Provide downloadable installers for Windows x64 and supported
  Linux x86_64 with a bundled CLI, runtime, and deployment files.
- **FR-002**: Document supported OS versions and external prerequisites, and
  detect missing or unusable deployment prerequisites.
- **FR-003**: Guide setup of the provider, private configuration, durable
  archive and state paths, Hindsight, and explicit bank provisioning.
- **FR-004**: Document start, stop, status, import, and installed-command MCP
  setup for Codex and Claude Code. MCP remains local stdio and read-only.
- **FR-005**: Preserve configuration, Hindsight data, archive and import state
  through a normal stop/start and reinstall.
- **FR-006**: Build both installers from a release tag using pinned build inputs.
  Reject a mismatch between the tag and the installed version.
- **FR-007**: Publish the installers, a SHA-256 for each, release notes and
  platform instructions on the GitHub Release.

### Key Entities

- **Release** — tag, version, platform assets, checksums and instructions.
- **Workstation configuration** — private provider settings, backend endpoint
  and storage locations shared by the operator and their local agent processes.
- **Persistent installation data** — Hindsight database, raw archive and
  SQLite import state, managed independently from installed executable files.

## Success Criteria

- **SC-001**: Both clean platform installs meet Story 1 and verify their
  checksums before executing either installer.
- **SC-002**: On both platforms the synthetic import completes and one fresh
  supported client recalls the expected decision and opens its source.
- **SC-003**: On both platforms, restart and reinstall preserve all four
  persistent components and unchanged imports are skipped.
- **SC-004**: Both packages can be built from `v0.1.0`, and the published page
  supplies both validated downloads, their checksums and installation steps.

## Assumptions

- Initial support is Windows 11 x64 and Ubuntu 24.04 LTS amd64. Expand the
  compatibility matrix only after testing additional platforms.
- The operator supplies Docker access and a compatible provider credential.
  Use one synthetic fixture and one supported client per platform for acceptance.
- Repeatability means a documented, pinned procedure from the same tag and
  matching package versions. Each published binary has its own checksum.
- The release tag is applied to the reviewed implementation after merge.
  Release signing is outside the issue's acceptance criteria.
