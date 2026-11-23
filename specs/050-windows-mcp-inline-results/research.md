# Research: Inline MCP Setup Results on Windows

## Progress page lifecycle

**Decision** — Snapshot selected rows before a pass and prevent scans during a progress-page return. Keep row results in the wizard page state. `ApplyMcpTargets` currently iterates the live checklist, and `CurPageChanged` calls `LoadMcpTargets` on each entry, including a return from `ProgressPage.Hide`.

**Alternatives** — Guarding the reload alone leaves the apply loop dependent on live controls and provides no retry or reconciliation model. Replacing the progress page with inline progress alone avoids one callback but leaves the selection and consent vulnerable to future page refreshes. Retain the existing progress page and protect its transition.

## Profile identity and authorization

**Decision** — Reconcile UI rows by normalized absolute Windows configuration path and the exact discovered client group. Use the existing review token for apply. `setup_clients.Snapshot.token` binds the normalized path, file identity, metadata and contents. `cli.setup._mcp_scan` additionally binds the grouped client IDs. `mcp-apply` rescans and requires a matching token, while the write path rechecks the reviewed snapshot. A changed token requires fresh selection, with fresh explicit confirmation for any conflict. Blocked rows lacking a profile path are display-only.

**Alternatives** — Row position or display text alone can associate results with another profile. Keeping the consent token as the sole display key loses retry and result context after a legitimate save changes the file. Adding a new helper field duplicates profile data already present in the existing protocol.

## Interaction and verification

**Decision** — Keep the user on the MCP page after an explicit check. Provide rescan for newly installed or changed profiles. Retain the per-record replacement prompt and maintenance confirmation for writes. The compiled test drives the actual wizard and uses a controlled helper fixture. Live Codex and Claude Desktop acceptance confirms real persistence and local probes separately.

**Alternatives** — Using **Next** for both checks and navigation makes the action ambiguous after a failure. A source-text assertion or a pure helper test cannot observe Inno's progress callback. The issue does not specify alternative approaches or a governance change.
