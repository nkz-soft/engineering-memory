# Feature Specification: Windows Installer Maintenance

**Feature Branch**: `049-windows-installer-maintenance`
**Created**: 2026-11-23
**Status**: Draft
**Input**: [Issue #120](https://github.com/nkz-soft/engineering-memory/issues/120)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure an existing build (Priority: P1)

A Windows operator reruns an identical installer to edit private settings or connect MCP clients. The wizard offers configuration or exit before it changes installation files.

**Why this priority**: Configuration is the primary reason to rerun an identical package.

**Independent Test**: Reopen a healthy installation with its original installer and compare the installed files and profiles before and after both the exit and configuration paths.

**Acceptance Scenarios**:

1. **Given** a healthy installation of the incoming version and build, **When** the operator opens configuration, **Then** the wizard shows the existing settings and available MCP targets without reinstalling the payload.
2. **Given** an identical build, **When** the operator exits or cancels before confirming changes, **Then** the payload, settings and MCP profiles are unchanged.
3. **Given** an identical build, **When** the operator confirms a settings change and selects no MCP target, **Then** only the intended settings change. An explicitly selected MCP change follows the existing inspection and confirmation rules.

### User Story 2 - Install, update or recover (Priority: P2)

A Windows operator sees how the incoming package relates to their current installation before choosing an operation.

**Why this priority**: Preserving the installed workspace and identifying the package accurately lets operators accept updates safely.

**Independent Test**: Start from clean, older, newer, same-version different-build and damaged installations in separate fixtures. Check the available actions and the resulting installation and user data.

**Acceptance Scenarios**:

1. **Given** no current-user installation, **When** the operator runs the setup, **Then** the normal install, guided configuration, MCP selection and optional startup are offered.
2. **Given** a healthy older installation, **When** the operator accepts the update, **Then** the wizard shows both versions, installs in place and records the incoming identity.
3. **Given** a healthy installation at the same version with a different build identity, **When** the operator proceeds, **Then** an explicit replacement is required before files change.
4. **Given** an older incoming package, **When** the operator runs it, **Then** the wizard explains the downgrade block and directs the operator to an appropriate package.
5. **Given** missing, damaged or unverified installation files, **When** the operator runs the setup, **Then** it offers explicit repair where the package can safely be used or explains how to obtain a suitable package. It never offers configuration against that installation.
6. **Given** a seeded workstation, **When** the operator accepts an update without editing settings or registrations, **Then** the private settings, archive, import state, Docker volume and profiles survive and the same synthetic imported result is still findable.

### User Story 3 - Deploy without interaction (Priority: P3)

A Windows operator uses silent setup for a deployment and can tell whether the package was installed, skipped or rejected.

**Why this priority**: The silent path must safely support unattended deployment.

**Independent Test**: Run both silent switches against the installer state matrix. Check process results and compare application and profile snapshots.

**Acceptance Scenarios**:

1. **Given** a fresh or healthy older installation, **When** setup runs silently, **Then** it installs or updates the payload and leaves private settings, MCP and startup alone.
2. **Given** a healthy identical installation, **When** setup runs silently, **Then** it succeeds as a no-op with no configuration or payload writes.
3. **Given** an older package, an unverified or damaged installation, or an equal-version replacement, **When** setup runs silently, **Then** it reports a non-success result with an actionable reason and leaves installed state unchanged.

### Edge Cases

- An existing uninstall entry with missing files, a leftover payload with no valid registration, or an installation from before build identity was recorded is existing but unverified.
- A valid installed version remains ordering evidence when payload evidence is incomplete. Conflicting valid version evidence blocks automatic decisions.
- An interrupted update must not leave broken files labelled healthy or start the stack. A retry must be able to reclassify the current installation and offer recovery.
- A running application must remain running for a no-op or configuration-only run. Where files are in use during a payload update, surface the normal installer conflict and avoid configuring a partially installed build.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Setup MUST classify the current-user installation before writing installation files: fresh, identical, newer incoming version, different build at the same version, older incoming version, or incomplete/unverified.
- **FR-002**: Setup MUST compare the release version and stable build identity independently. A build identity MUST distinguish different packaged content at the same version and MUST carry no ordering semantics. Identical status requires verified installed payload evidence.
- **FR-003**: Identical interactive setup MUST allow configuration or exit with no payload, uninstall registration or user PATH changes. Exiting before final confirmation MUST leave settings and MCP profiles unchanged.
- **FR-004**: Install and update MUST retain the existing guided setup and optional startup. A version update MUST display both versions. Equal-version replacement and recovery MUST require explicit consent to copy files. Downgrade MUST be blocked.
- **FR-005**: Setup MUST preserve private provider settings, credentials, selected ports and proxies, raw archive files, SQLite import state, Docker volumes and unrelated MCP registrations across supported paths. Settings and target registrations change only when explicitly selected and confirmed.
- **FR-006**: Silent setup MUST implement the documented matrix for install, update, no-op and rejection, with zero interactive helper calls, and provide an actionable diagnostic for rejection without leaking private data.
- **FR-007**: Successful payload operations MUST record the incoming build identity. Subsequent runs MUST detect and explain incomplete or corrupt installations and provide a recoverable path without treating them as ready.
- **FR-008**: Automated Windows installer coverage MUST exercise classification, file and profile preservation, and silent acceptance/rejection. Manual Windows acceptance MUST exercise identical-build configuration, explicit same-version replacement and version update using verified artifacts.

### Key Entities

- **Incoming package** — release version and stable content identity.
- **Current-user installation** — installed files, version/build evidence and observed health. Its profile and data survive payload operations.
- **Maintenance decision** — detected relationship, selected operation and the consent needed to write anything.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All six installer outcomes are distinguishable before payload writes in automated fixtures and the documented operator flow.
- **SC-002**: Identical-build exit and silent runs leave files and profiles unchanged. Interactive configuration changes only the confirmed fields and selected MCP entries.
- **SC-003**: Each accepted update records the incoming identity. A seeded synthetic import is retrievable with the same provenance after the update, and persistence checks cover the settings, credentials, ports, proxies, archive, SQLite state, Docker volume and an unrelated MCP entry.
- **SC-004**: Both silent flags match the documented outcome matrix, including zero payload changes for identical and blocked packages and zero configuration, registration or startup activity for every silent outcome.
- **SC-005**: Verified Windows installer artifacts demonstrate all three manual maintenance scenarios in FR-008.

## Assumptions

- Scope is the Windows 11 x64 per-user workstation installer from [#105](https://github.com/nkz-soft/engineering-memory/issues/105), including the existing wizard and MCP consent from [#119](https://github.com/nkz-soft/engineering-memory/pull/119). The Ubuntu installer and application data formats are outside this change.
- A known older package is blocked in every mode. Where trustworthy ordering evidence is unavailable, use the latest verified installer for interactive recovery. Legacy installations require an explicit one-time recovery or migration before they can qualify for configuration-only mode.
- Silent updates are allowed when the incoming version is strictly newer and the installed build is healthy. Same-version replacement and recovery are interactive operations.
- Cancellation is available before confirmation of the configuration changes. Once confirmed, existing save, stale-edit and per-target apply outcomes govern retries. The configuration-only path does not start the stack.
