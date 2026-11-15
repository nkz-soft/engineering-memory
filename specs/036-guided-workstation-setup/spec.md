# Feature Specification: Guided Workstation Setup

**Feature Branch** `036-guided-workstation-setup`
**Created** 2026-11-14
**Status** Draft
**Input** [Issue #94](https://github.com/nkz-soft/engineering-memory/issues/94)

## User Scenarios & Testing

### User Story 1 - Configure and start a workstation (Priority P1)

A first-time user completes setup from the installation flow, enters provider credentials privately, selects storage and ports, and gets a working backend with its shared memory bank provisioned.

**Independent test** Install on each supported operating system and finish setup with no file edits, then verify readiness and retry using the existing values.

1. **Given** a clean supported machine with compatible Docker and valid credentials, **when** the user completes the prompts, **then** setup saves private settings, starts the backend and provisions the bank.
2. **Given** Docker is unavailable, the port is busy or provisioning fails, **when** setup attempts readiness, **then** the user sees the failed stage and a retry path. Import stays deferred.
3. **Given** an existing installation, **when** the user accepts the current settings, **then** setup retains existing credentials and storage and can resume from a prior failure.

### User Story 2 - Connect selected coding agents (Priority P2)

A user sees detected Codex and Claude Code installations and profiles and chooses which to configure.

**Independent test** Use isolated profiles with unrelated settings, run setup twice, and open fresh sessions in selected clients.

1. **Given** one or both clients are detected, **when** the user selects a client, **then** its profile registers the installed read-only memory server and a fresh session can discover the tools.
2. **Given** a matching registration, **when** setup runs again, **then** it reports the existing registration and creates no duplicate.
3. **Given** an existing registration with the same name and a different target, **when** setup detects it, **then** it preserves the entry unless the user explicitly approves replacing that entry.

### User Story 3 - Select and import existing history (Priority P3)

A user reviews eligible local histories and exports and can import selected sources or defer the step.

**Independent test** Seed supported agent histories and local chat exports with synthetic facts, select a subset, then verify recall and source access through MCP.

1. **Given** supported local history and exports, **when** setup reaches discovery, **then** it shows source types and locations before any import.
2. **Given** a supported export outside the discovery locations, **when** the user supplies its path and selects it, **then** setup imports it after provisioning.
3. **Given** one selected source fails and another succeeds, **when** the run ends, **then** setup reports imported, skipped and failed items and allows a retry of the failed source.

### Edge Cases

- Absent clients and empty history are valid. A detected profile without a usable registration command is shown with manual instructions.
- Canceling a prompt leaves previously saved settings usable. Canceling or skipping registration or import leaves unselected targets untouched.
- Invalid input is explained at the stage where it occurs. Error output omits secret values and conversation content.
- Silent or unattended installation completes without starting an interactive wizard.

## Requirements

### Functional Requirements

- **FR-001** The Windows 11 x64 interactive installer MUST offer guided setup after installing the app. Ubuntu 24.04 LTS amd64 installation instructions MUST lead directly to the same installed setup command, run from the user's own session after package installation. The command MUST be independently rerunnable.
- **FR-002** Setup MUST prompt for the provider, model, credential and custom endpoint when applicable, the local backend ports, archive location and SQLite path. It MUST show useful defaults and existing nonsecret values, validate inputs and allow existing secrets to be retained without showing them.
- **FR-003** Setup MUST save credentials in the private local profile and keep credentials out of logs, summaries, process arguments and MCP registrations. It MUST preserve unrelated settings, archive and SQLite contents across retry and reinstall.
- **FR-004** Setup MUST check Docker access, guide startup, report readiness and provision the existing shared bank before import. A failed readiness step MUST prevent history writes and show a recovery action.
- **FR-005** Setup MUST show detected Codex and Claude Code installations and user profiles, including supported profile overrides, and apply registration only to selected clients. It MUST preserve unrelated configuration and avoid duplicates.
- **FR-006** A selected client MUST register the absolute installed command with the read-only server entry point and no embedded credentials. Conflicts MUST be surfaced before any replacement.
- **FR-007** Setup MUST list eligible Codex and Claude Code histories in active user profiles and supported local ChatGPT and Claude chat exports from known locations or a user-entered path. A source MUST be identifiable by kind and location before selection.
- **FR-008** Setup MUST allow skip or defer without importing anything unselected. Selected sources MUST use existing supported importers with stable identity and normal re-import behavior. Setup MUST report imported, skipped and failed counts per selected source and distinguish sources skipped by the user from skipped conversations.
- **FR-009** Setup MUST provide actionable outcomes for registration and import failures, preserving completed work and allowing retries. Manual setup MUST remain available.

### Key Entities

- **Workstation profile** holds effective provider, endpoint, ports and persistent paths, plus private credentials.
- **Client target** identifies a supported installed client and active user profile, with its registration status.
- **History candidate** identifies a supported source kind and local path, with optional explicit selection.
- **Setup outcome** records stage results and safe import counts for the current run.

## Success Criteria

### Measurable Outcomes

- **SC-001** Complete fresh installation and setup on both supported platforms without editing configuration files. Confirm private settings, backend readiness and bank provisioning.
- **SC-002** Select Codex and Claude Code in isolated user profiles. Each fresh client discovers the read-only tools, and existing unrelated entries survive.
- **SC-003** With supported synthetic agent history and chat exports present, import selected sources only. Recall a known decision and open its sanitized source conversation through MCP.
- **SC-004** Retry or reinstall with existing settings. Credentials and data survive, each selected profile has one registration, and re-import of unchanged history creates zero new retained documents.
- **SC-005** Use a synthetic credential and confirm it is absent from terminal output, logs, MCP registrations and process arguments. Verify private-file access on both platforms.

## Assumptions

- Guided setup is a terminal workflow. A typed path satisfies export selection on both platforms.
- The existing installation targets, Docker requirements and local backend remain the supported baseline.
- Client discovery considers the current user's active profile for each supported client. Setup does not enumerate other accounts or scan arbitrary directories for exports.
- Chat exports come from a configured inbox, supported files discovered there, or paths the user supplies. Cloud export acquisition and new history formats are outside this feature.
- Setup is interactive and optional. Existing scriptable install and operator commands remain usable.
