# Feature Specification: Workstation outbound HTTP(S) proxy

- **Feature Branch**: `046-workstation-outbound-proxy`
- **Created**: 2026-11-20
- **Status**: Draft for approval
- **Input**: [GitHub #107](https://github.com/nkz-soft/engineering-memory/issues/107)

## User Scenarios & Testing

### User Story 1 - Configure provider egress during setup (P1)

A Windows or Ubuntu workstation operator on a proxy-required network can configure the installed LiteLLM service during guided setup and send an LLM request to the configured provider.

**Independent test**: Use the installed CLI and bundled stack with a synthetic provider behind a controlled forward proxy. Block direct access to the provider from LiteLLM while preserving access from the proxy.

1. **Given** the provider is inaccessible directly, **when** the operator saves the correct proxy settings and starts the stack, **then** a synthetic completion succeeds, the proxy records the corresponding request or tunnel, and local services stay healthy.
2. **Given** a configured proxy is unreachable or rejects the connection, **when** the operator checks the provider route, **then** setup reports how to check the proxy address, access or credentials without printing secret values.

### User Story 2 - Change or remove a saved route (P1)

An operator can revisit guided setup to keep, replace or clear the proxy settings. An existing profile without proxy settings can still be used without migration.

**Independent test**: On both platforms, rerun setup with the same profile and verify the effective route after each stack start.

1. **Given** an existing route, **when** the operator saves a replacement or clears it, **then** the next stack start uses the replacement or removes workstation-managed proxy routing.
2. **Given** invalid input or a cancelled edit, **when** the operator leaves setup without confirming, **then** the saved settings remain intact.

### User Story 3 - Identify the correct setting (P2)

The operator can use the guide to distinguish the network forward proxy URL from the OpenAI-compatible provider API base and choose an address reachable from inside the LiteLLM container.

**Independent test**: Follow the guide on a workstation with a host-based proxy and a separately addressed test provider.

### Edge Cases

- Local defaults cover loopback and the Hindsight and LiteLLM service names even when the operator adds bypass entries.
- An HTTPS provider may use an HTTP proxy through CONNECT. Proxy endpoint scheme and provider scheme are independent.
- Missing settings, invalid URLs, URL-encoded credentials, interrupted profile updates, and proxy authentication failures receive coverage.

## Requirements

### Functional Requirements

- **FR-001**: Guided setup on installed Windows and Ubuntu workstations MUST support keeping, setting, changing and clearing optional outbound HTTP and HTTPS proxy URLs and additional bypass hosts without manual file edits.
- **FR-002**: The workstation MUST store values with the existing private Compose profile and apply changes to the bundled LiteLLM container on the next stack start. Legacy profiles and unset settings MUST preserve existing workstation behavior.
- **FR-003**: LiteLLM MUST support `HTTPS_PROXY`, `HTTP_PROXY` where applicable and `NO_PROXY`. Local stack traffic MUST use direct connections, with loopback and the Hindsight/LiteLLM service names in the mandatory bypass.
- **FR-004**: The provider API base MUST remain an independent setting that controls the provider destination. Proxy credentials MUST use secret input and stay out of CLI output, logs and acceptance evidence.
- **FR-005**: A failed provider-route check with a configured proxy MUST return actionable, sanitized guidance for reachability or access failures.
- **FR-006**: The workstation guide MUST cover URL format, container reachability, bypass defaults, provider API base, and how to change or clear the route.

### Key Entities

- **Workstation proxy settings**: Optional URLs for outbound HTTP and HTTPS and optional additional `NO_PROXY` entries, persisted in the private profile.
- **Provider route**: Existing provider destination plus the effective LiteLLM-only proxy and bypass configuration.

## Success Criteria

- **SC-001**: Installed setup on Windows and Ubuntu passes a set, replace and clear cycle plus a legacy-profile regression check.
- **SC-002**: On both platforms, a synthetic completion through installed LiteLLM returns the expected response with the direct provider route blocked. A matching proxy observation and a failed direct control verify the route while local services report healthy.
- **SC-003**: Unreachable and rejecting proxies produce retry guidance. Synthetic credential markers are absent from captured prompts, CLI output, logs and retained evidence.
- **SC-004**: The guide provides a container-reachable example and explains the independent endpoint, bypass and update controls.

## Assumptions

- Setup controls the installed LiteLLM route. Docker daemon proxying, image pulls, and system proxy configuration have their own settings.
- The wizard offers explicit Keep, Set and Clear choices for each URL. Additional bypass entries extend mandatory defaults.
- A user-initiated synthetic provider check may consume one completion. The controlled acceptance uses only fixture data and credentials.
- Ubuntu validation uses the installed release flow from #105 / PR #106 once available on main.
