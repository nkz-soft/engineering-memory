# Feature Specification: Inline MCP Setup Results on Windows

**Feature Branch**: `050-windows-mcp-inline-results`
**Created**: 2026-11-23
**Status**: Draft
**Input**: [Issue #121](https://github.com/nkz-soft/engineering-memory/issues/121)

## User Scenarios & Testing

### User Story 1 — Check several clients in one pass (P1)

A Windows user selects the existing Codex CLI / Codex Desktop profile and a Claude Desktop profile that needs registration. The wizard verifies Codex, saves and verifies Claude Desktop, and leaves a third unchecked profile untouched. If Codex fails, Claude Desktop is still attempted.

**Independent test** — Run both selected rows through the compiled wizard, including a return from the progress page after the first row. Repeat with that first row failing. Verify both attempts, the resulting Claude Desktop entry and the untouched third profile.

### User Story 2 — Review outcomes and retry (P1)

After a pass, the user stays on **Connect MCP clients**. The list shows registration and local check outcomes. Focusing a row shows its safe diagnostic and any restart guidance. The user can select and retry a failed row or continue directly.

**Independent test** — Exercise a failed check after a successful save, then retry with an updated scan. Verify that the row shows both outcomes, the retry uses the same profile, and the Codex CLI `service_tier` warning remains available when applicable.

### User Story 3 — Control conflicting replacements (P1)

The user can keep an existing conflicting registration or explicitly confirm replacing the reviewed entry. If the profile or its configuration changes after review, the wizard reports the stale request and requires fresh review.

**Independent test** — Decline, accept, and independently alter a conflicting entry between confirmation and apply. Compare the affected record and unrelated settings before and after each run.

## Functional Requirements

- **FR-001** — The wizard MUST capture the selected, actionable profiles and their reviewed configuration as one pass before any per-client progress transition. Each selected profile MUST receive at most one attempt in that pass, even when another attempt fails.
- **FR-002** — The list MUST show actual registration outcomes, including saved, already configured, kept, failed and skipped where applicable, and independently show the local check outcome. A profile whose execution or response failed MUST show the check as unavailable when its result is unknown.
- **FR-003** — The detail area MUST follow keyboard and mouse focus and retain safe profile diagnostics, existing restart guidance and the Codex CLI `service_tier` warning when applicable. Routine progress and per-client results MUST appear without a modal summary.
- **FR-004** — Each pass MUST leave the page open. The operator MUST be able to continue with failures present and retry only selected profiles. Retrying an already saved registration MUST use the current review and perform a local check without rewriting a matching entry.
- **FR-005** — Replacement MUST require an explicit decision for the exact reviewed entry. Declining MUST preserve that entry and show kept / check skipped inline. A stale review MUST yield no replacement and require a new decision after rescan.
- **FR-006** — A rescan MUST reconcile only a profile that can be identified unambiguously. Changed or unresolved targets MUST require fresh selection before a write, and fresh replacement consent if in conflict. Unchecked profiles MUST remain unchanged.
- **FR-007** — Apply the behavior to interactive fresh install and configuration-only maintenance. Preserve existing settings validation, maintenance consent, and silent installer behavior.

## Assumptions and Scope

- Use a dedicated **Check selected clients** action and wizard navigation to continue. In maintenance mode, **Apply** still covers staged settings changes when no client check has been requested.
- A row represents the discovered configuration profile, including the existing shared Codex CLI / Desktop row. A local MCP check retains its existing meaning and the client can still need a restart.
- Changes are limited to the Windows Inno Setup wizard and its regression coverage. MCP server behavior, terminal setup and history import are outside scope. No governance change is requested.

## Success Criteria

- **SC-001** — Both selected rows are attempted after a progress-page return in both the normal and first-row-failure cases, with the third fixture unchanged.
- **SC-002** — The selected rows show independent registration and local check outcomes, and their detailed diagnostics can be reviewed before leaving the page.
- **SC-003** — Decline and stale-review cases leave the conflicting record unchanged. An accepted replacement updates only the reviewed record and preserves unrelated content.
- **SC-004** — Automated coverage exercises the compiled wizard through the progress-page return. A separate manual acceptance pass uses a compiled installer with real Codex and Claude Desktop profiles.