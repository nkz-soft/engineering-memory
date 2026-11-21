# Research: Workstation MCP Registration

## Decision — Native installation evidence and current-user profiles

Deduplicate Codex registrations by effective file. OpenAI documents shared MCP configuration for the same host and a default of `~/.codex/config.toml`. Account for `CODEX_HOME` when that client launch actually inherits it. Discover Windows Desktop via the current user's registered vendor package and Ubuntu Desktop from the official `chatgpt` package/launcher. Verify the exact supported Windows package identities and Linux launch metadata when writing fixtures. Do not infer CLI presence from an executable embedded in either Desktop app.

Discover Claude Code by supported CLI installation markers, including a native per-user binary outside PATH. Resolve its user MCP store using `workstation_agent_profiles()` and validate override behavior against the actual CLI. For Claude Desktop, probe documented vendor package metadata, the roaming layout, and the packaged per-user layout. Include the observed Windows virtualized `AppData/Roaming/Claude-3p/claude_desktop_config.json` inside the current user's package profile. Resolve the selected active profile with package identity and known layout evidence, with no broad scan and no guessing when multiple active candidates remain. On Ubuntu, include the official `claude-desktop` DEB and validate the XDG/default Claude user-data mapping against that package and its **Edit Config** action before release. Treat exact vendor package/profile mappings not specified in docs as implementation verification, and the observed Windows 3P layout as required.

Sources: [OpenAI MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), [OpenAI Windows app](https://learn.chatgpt.com/docs/windows/windows-app), [OpenAI Linux preview](https://learn.chatgpt.com/docs/linux/linux-app), [Claude Code settings](https://code.claude.com/docs/en/settings), [Claude Desktop Windows deployment](https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows), [Claude Desktop Linux beta](https://code.claude.com/docs/en/desktop-linux), [Claude Desktop on 3P](https://claude.com/docs/third-party/claude-desktop/overview), [MCP SDK Desktop config](https://py.sdk.modelcontextprotocol.io/get-started/real-host/).

Profile directories alone can survive uninstall, and running a vendor CLI for discovery can fail for reasons unrelated to installation. Use CLI validation, if available and useful, only as separate compatibility evidence, with bounded execution and sanitized diagnostics.

## Decision — Preserve the existing entry unless an authorized edit succeeds

Compare installed executable, exact argument list, transport and effective launch settings. Treat commands from existing entries as data. Inspect Codex TOML independent of the client's schema validation. The observed npm Codex rejects `service_tier = "default"`; an isolated profile re-read and MCP handshake may still succeed, and that is distinct from Codex being able to load the profile. A source-checkout command is a conflict even if it exposes the same tools. Editing that entry must preserve the unrelated setting. Keep profile parser output and existing command/env values out of helper output.

Vendor add/remove commands cannot cover Desktop-only or the version mismatch. A remove-then-add flow could lose the existing registration on failure. A controlled round-trip file edit avoids both problems.

## Decision — Use packaged stdio as the server proof

Reuse the isolation pattern from `packaging/workstation/smoke.py`. An SDK client performs `initialize`, the initialized notification and `tools/list` without using the workstation backend, archive or real credentials. A synthetic successful handshake confirms the server under installer verification conditions. A fully restarted, authenticated client session is separate acceptance evidence. The full #71 retrieval workflow is independent.
