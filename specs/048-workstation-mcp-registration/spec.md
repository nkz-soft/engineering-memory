# Feature Specification: Workstation MCP Registration

**Feature Branch**: `048-workstation-mcp-registration`
**Created**: 2026-11-21
**Status**: Draft for approval
**Input**: [Issue #109](https://github.com/nkz-soft/engineering-memory/issues/109), [installer wizard #111](https://github.com/nkz-soft/engineering-memory/pull/111)

## User Scenarios & Testing

### User Story 1 - Connect installed clients during installation (Priority: P1)

A workstation user can select the installed clients that should gain access to Engineering Memory during an ordinary interactive install.

**Why this priority**: A user with only a desktop app should be able to connect it from the installer.

**Independent Test**: Install using the normal interactive entry point with one supported desktop app and confirm the offered target and persisted registration.

1. **Given** one supported client is installed, **when** the normal installer reaches client setup, **then** it identifies that client and its current-user profile and offers registration before finishing.
2. **Given** two Codex clients use one profile, **when** the user opts in, **then** setup writes one entry and shows the outcome for both clients. Clients with different effective profiles are offered separately.
3. **Given** no supported clients are installed, **when** setup scans, **then** it completes or offers to continue without creating client profiles.

### User Story 2 - Inspect and preserve existing registrations (Priority: P1)

A workstation user can rerun setup or reinstall while keeping existing client configuration and choosing whether to replace conflicting entries.

**Why this priority**: An upgrade may encounter a working registration or a registration pointing at a source checkout.

**Independent Test**: Seed default and custom profiles with current, missing and conflicting entries and compare the files after accepting and declining each operation.

1. **Given** an absent entry, **when** the user opts in, **then** setup adds the installed absolute executable path with the argument `serve`.
2. **Given** a matching entry, **when** setup runs, **then** the entry remains untouched. Given a conflict, replacement requires explicit confirmation and changes only that entry.
3. **Given** the Windows npm Codex CLI rejects `service_tier = "default"`, **when** setup inspects that profile, **then** it can identify the registration from the file and report any client compatibility limitation while preserving the unrelated setting.

### User Story 3 - Know whether the tools are available (Priority: P2)

A workstation user sees whether the profile is saved and whether the local MCP server exposes both tools. The user can then check the result in a fresh client session.

**Why this priority**: The persisted entry, the server response and the client's ability to use it each need their own evidence.

**Independent Test**: Exercise a valid installed server and a server that times out or omits a required tool, then complete the restart checklist with a real client.

1. **Given** a selected profile contains a matching entry, **when** setup re-reads and verifies it, **then** success requires `initialize` and `tools/list` containing both `search_memory` and `get_conversation`.
2. **Given** verification fails, **when** the installer reports the result, **then** the saved configuration status remains visible and the user gets a retry path.
3. **Given** the installer has reported local verification, **when** the operator restarts each supported client and opens a fresh session, **then** the checklist records whether both tools are visible there.

### Edge Cases

- A leftover profile, embedded Desktop helper, foreign account installation or unsupported distribution can resemble a supported client. Discovery requires supported installation evidence.
- If several profile locations could be active, setup reports the ambiguity and gives an actionable next step. It writes only to a resolved target.
- A malformed, redirected, inaccessible or concurrently modified file yields a diagnostic. A failed replacement leaves the prior entry usable.
- A client command unavailable from the installer can still have a resolvable profile. Setup uses a supported profile-based path or reports the limitation.
- Paths may contain spaces or Unicode. An existing transport may be disabled, point elsewhere, use a different transport, or change process launch behavior.
- A hung or broken server or missing tools must fail local verification within 30 seconds per distinct selected profile. A failure for one target leaves the others available for setup.

## Requirements

### Functional Requirements

- **FR-001**: Discover current-user Codex CLI, Codex Desktop, Claude Code CLI and Claude Desktop on Windows 11 x64 and Ubuntu 24.04 LTS amd64. Include vendor-supported Desktop previews on Ubuntu and documented package layouts, including the Windows packaged `Claude-3p` profile.
- **FR-002**: Discover client identities independently of profile existence. Resolve supported custom profile locations and deduplicate by effective configuration file. Detect a desktop-only installation without relying on its vendor's CLI.
- **FR-003**: Offer registration in the regular interactive Windows installer using the built-in wizard from #111 and in the Ubuntu installer's guided setup. Standalone setup supports retries. Consent is opt-in per resolved profile and replacement requires a separate opt-in. Silent install and deferral perform no client writes. Preserve existing workstation configuration, startup and optional history import behavior.
- **FR-004**: Inspect each resolved profile and report an absent, matching, conflicting or unreadable registration. Add only `engineering-memory` using the absolute installed executable and `serve`. Leave matches byte-for-byte intact. Preserve unrelated settings and MCP entries on edits, detect stale consent and make writes atomic. Repeat runs create no duplicate entries.
- **FR-005**: Support profile-based inspection when a client executable is unavailable or incompatible. Give actionable diagnostics for blocked registration or client loading, including the observed Codex npm `service_tier = "default"` case without changing that setting.
- **FR-006**: Re-read selected registrations, then run bounded local stdio `initialize` and `tools/list` for the verified installed target. Require `search_memory` and `get_conversation`. The probe must avoid reading history or credentials and exclude secrets, command output and config contents from logs and diagnostics.
- **FR-007**: Report persisted registration and local handshake outcomes per client, including shared profiles, and explain restart and fresh-session checks. Local verification provides server evidence. Client-session availability is recorded separately.
- **FR-008**: Make a dedicated discovery check required on both installer platforms using isolated fixtures without client authentication or personal profiles. Exercise all subsets of platform-supported clients and each supported layout, including custom profiles, shared and distinct profiles, and installed/absent/unsupported signals. Assert the exact discovered clients and resolved targets and that absent or unsupported clients cause no profile writes.
- **FR-009**: Supply commit-linked, checksum-verifiable installer artifacts after implementation, with a short checklist for the operator to verify tool discovery in fresh real sessions on both platforms.

### Key Entities

- **Detected client**: Product identity, install evidence and current-user profile resolution.
- **Registration target**: One configuration file used by one or more clients, with its inspection, consent and persistence status.
- **Verification result**: Per-client persisted registration and local server status, with fresh-session evidence recorded separately.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The dedicated required CI check covers all 16 subsets of the four clients on each installer platform, plus the supported layout and negative fixtures, with exact comparison of identities and target counts.
- **SC-002**: Decline, silence, absence, matching entries and failed writes leave the affected client files intact. Each confirmed add or replace yields exactly one entry per selected profile.
- **SC-003**: A selected matching registration can be verified offline within 30 seconds per profile, and every timeout or missing required tool yields a failure status.
- **SC-004**: The operator can identify the exact tested installer by commit and checksum and record visibility of both tools in a fresh session for every supported client and platform, including the Windows Desktop-only cases.

## Assumptions

- Use the local native client host and current login account. WSL, remote hosts, third-party repackagings and writes to project, organization or managed configuration are outside automatic registration. A known override or policy that prevents use of the user entry receives a diagnostic.
- Desktop support on Ubuntu includes the official OpenAI preview and Anthropic beta available for Ubuntu 24.04. Record verified package/profile mappings and test them before acceptance.
- The MCP step defaults to skip and remains available when the user defers backend startup and import. The handshake checks tool descriptors without tool calls. The full real-agent memory scenario remains in [#71](https://github.com/nkz-soft/engineering-memory/issues/71).
