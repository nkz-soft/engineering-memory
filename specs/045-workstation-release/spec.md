# Feature Specification: Workstation Release v0.0.1

**Feature branch**: `045-workstation-release`
**Created**: 2026-11-20
**Status**: Draft
**Input**: [Issue #105](https://github.com/nkz-soft/engineering-memory/issues/105)

## User Scenarios and Testing

### User Story 1 — Install and start from release assets (P1)

A workstation user follows the release guide and starts one installer. After granting any required OS permissions and entering provider settings in the guided setup, the user can run the installed command and use the local backend.

1. Given a clean Windows 11 x64 or Ubuntu 24.04 LTS amd64 workstation with the documented prerequisites, when the user verifies the downloads and runs the supported installer, installation proceeds into guided setup in the same user session without a separate command.
2. Given valid provider inputs, when guided setup completes, the installed CLI reports `0.0.1`, the local stack reports ready and the shared bank is provisioned. The user can decline optional client registration and history import and still finish setup.
3. Given Docker is unavailable, package installation fails, or backend startup is interrupted, the workflow identifies the failed stage and gives a recovery action. It does not report readiness or begin an import.

### User Story 2 — Verify a working installation and recover it (P2)

1. Given the installed product and a synthetic conversation, when the user imports it and accesses memory through the installed MCP server from another directory, the expected decision and sanitized conversation are retrievable with the original timestamp and stable identity.
2. Given a working installation, when the user restarts the stack and reinstalls the same release, private settings, the archive, import state and retained data remain available. An unchanged re-import is skipped.

### User Story 3 — Publish a verified release (P3)

Given the exact draft artifacts have passed workstation acceptance on both supported systems, the maintainer publishes `v0.0.1` with instructions and verifies the public downloads against the digests in the acceptance record.

## Requirements

- **FR-001**: Project metadata, the lockfile, CLI version, release tag and distributed package metadata and names MUST agree on `0.0.1`. The release MUST include platform assets and matching SHA-256 sidecars.
- **FR-002**: The supported interactive path on each OS MUST install the bundled CLI and runtime and automatically launch guided setup in the signed-in user's session. Installation MUST NOT require a checkout, user-managed Python or uv, manual file edits, or separate setup, start or provision commands. The Windows silent path MAY install the payload without launching a wizard and MUST be described accordingly.
- **FR-003**: The workflow MUST detect unavailable or unsupported Docker with an actionable message before collecting provider inputs. Guided setup MUST preserve the private user profile, wait for local Hindsight and LiteLLM readiness and provision `engineering-global` before optional imports.
- **FR-004**: Failed or deferred setup MUST be distinguishable from a ready backend and support retry without deleting data or disclosing credentials. Repeat installation and restart MUST preserve profile, archive, import state and backend data.
- **FR-005**: The installation guide MUST cover supported OS versions, prerequisites, downloads, checksums, permissions, provider prompts, status, stop/restart and failure recovery. README and release notes MUST link to it.
- **FR-006**: Before publication, record the OS, candidate commit/tag, exact installer digests, commands and outcome for both clean-workstation runs. After publication, verify the public downloads against the accepted digests.
- **FR-007**: Real-agent acceptance from [#71](https://github.com/nkz-soft/engineering-memory/issues/71) remains a separate manual run after installation, with its evidence recorded in that issue's workflow.

## Success Criteria

- **SC-001**: Each supported OS passes one installer-to-ready run using the exact draft assets. After starting the installer, the user enters zero separate configuration or lifecycle commands.
- **SC-002**: Each run verifies installed version, stack readiness, a synthetic import and MCP retrieval, restart, reinstall and unchanged-import skipping. At least one actionable failure path is exercised on each OS.
- **SC-003**: Public asset digests match the accepted draft on both platforms.

## Assumptions

- Docker Engine 28 or newer and Compose 2.24.4 or newer are system prerequisites. On Windows Docker Desktop runs Linux containers. The user has Docker access and a compatible LLM provider.
- One installer invocation allows interactive provider input, required OS permissions and optional client/import decisions. It does not imply unattended configuration.
- This is first-release acceptance and same-version reinstall testing. A workstation with an unreleased `0.1.0` package uses a clean profile or follows documented package-manager guidance. The launcher handles refusal without starting an older or mismatched setup.
