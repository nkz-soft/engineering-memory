# Feature Specification: Windows installer configuration page

- **Feature Branch**: `047-windows-setup-ui`
- **Created**: 2026-11-21
- **Status**: Draft for approval
- **Tracking**: Follow-up to [#94](https://github.com/nkz-soft/engineering-memory/issues/94) and [#105](https://github.com/nkz-soft/engineering-memory/issues/105)

## User Scenarios & Testing

### User Story 1 - Configure a fresh Windows installation (P1)

A Windows 11 x64 user can configure the provider and local data from the normal interactive installer.

1. Given a fresh profile, when the user runs the interactive installer, the configuration page opens before Finish without launching a console. Provider, model, masked API key, provider API base, memory backend port, LiteLLM port, archive directory, and SQLite file are editable.
2. When the user saves valid settings, the installer writes a usable per-user profile. When they defer or cancel before saving, no new settings are applied. Declining startup still permits saving and finishing.
3. When they explicitly authorize starting the stack and provisioning the shared bank, the installer shows the outcome. A failed step gives a retry or deferral path and leaves any successfully saved configuration available.

### User Story 2 - Reinstall with an existing profile (P1)

Given existing settings, including outbound HTTP(S) proxy and bypass settings, reinstalling shows the saved nonsecret values. A blank masked key field keeps the saved key for the same provider. Choosing another provider requires an explicit replacement key. Saving an unrelated field preserves proxy settings, the local LiteLLM key, archive content, SQLite state, and backend data. Legacy profiles remain usable.

### User Story 3 - Automate installation or return to CLI setup (P2)

A silent install completes with the current package and PATH behavior, skips setup UI, and leaves the private profile and stack alone. After an interactive or silent install, `engineering-memory setup` remains usable for configuration, outbound proxy changes, optional MCP registration, and optional history import.

### Edge Cases

- Invalid, identical, or out-of-range ports and invalid paths or provider inputs produce field guidance before saving. Occupied ports and unavailable Docker are actionable startup failures.
- Cancel, a competing setup writer, or an interrupted profile write leave a coherent profile. A failure after saving may leave the stack running and must identify what succeeded.
- Existing model IDs, blank API base, spaces and Unicode in storage paths, and saved secrets containing Compose-sensitive characters round-trip.

## Requirements

- **FR-001**: Show the embedded page by default on a standard first interactive Windows install and on interactive reinstall. Provide an explicit way to defer configuration to the CLI.
- **FR-002**: On a fresh profile propose backend port `8888`, LiteLLM port `4000`, archive under `%LOCALAPPDATA%/EngineeringMemory/data/archive`, and SQLite at `%LOCALAPPDATA%/EngineeringMemory/data/import-state.db`. For the OpenRouter preset, propose model `openai/gpt-oss-20b` and API base `https://openrouter.ai/api/v1`. All proposed values are editable.
- **FR-003**: Mask the provider credential. Keep its value out of process arguments, logs, installer answer files, and displayed diagnostics. Never return the stored credential to the page. Save a replacement only when the user supplies one.
- **FR-004**: Validate and save through the existing per-user profile rules. Preserve outbound HTTP(S) proxy URLs, bypass settings, unrelated profile assignments, the local proxy key, and storage on reinstall. The provider base remains separate from the outbound network proxy.
- **FR-005**: Ask for affirmative consent before starting the stack and provisioning the shared bank. The default is unchecked. Saving or declining does not start either action. Report the outcome of the approved operation and allow the user to retry or defer it.
- **FR-006**: Preserve silent installation and the terminal setup flow. Embedded setup does not register agents, import history or make a synthetic provider request automatically.

## Success Criteria

- **SC-001**: An installed Windows 11 x64 build passes fresh configuration, explicit startup and provisioning, save-only, and defer cases without a console in the embedded flow.
- **SC-002**: A reinstall with customized values and proxy credentials preserves the expected configuration and data. A controlled provider request through the installed LiteLLM route verifies the model mapping.
- **SC-003**: A synthetic key marker is absent from process arguments, setup output and logs in both successful and failing runs. Silent install leaves setup and the stack untouched. A subsequent terminal run can reconfigure the installation.

## Decision for approval

**Proposed**: preselect the editable OpenRouter preset for a fresh interactive Windows profile. **Alternative**: start with a neutral provider selector and fill the same suggested model and URL only when the user chooses OpenRouter. Both choices use the same page and leave existing profiles untouched. No provider is contacted while entering or saving settings.

## Assumptions and scope

This change covers Windows installer UX. Existing Ubuntu setup, release versioning, outbound proxy editing, and the memory data path have their existing entry points. Saving settings and starting services are separate actions. Optional MCP registration and history import remain available through terminal setup.
