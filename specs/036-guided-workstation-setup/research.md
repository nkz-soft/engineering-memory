# Research

## Use the bundled CLI as the installer handoff

The Windows installer already runs at the lowest privilege level and updates user PATH after installation. Offer a post-install launch using the installed absolute executable and skip it in silent mode. The Ubuntu package installs the launcher under `/usr/bin` through a system package transaction. Put the next command in the installation steps so the person who ran apt can launch the wizard as their ordinary user. See [the current installer guide](../../docs/operations/workstation-install.md).

## Use the existing profile and lifecycle

Load the effective workstation values, preserve unknown entries, and use the existing per-user paths and dotenv conventions. Validate values before writing, stage private replacements, serialize concurrent wizard runs and recover the pair if one write fails. Generate a proxy key only for a new profile that has no usable key. Use the current Compose check and wait path, then provision through the same operator path as the CLI. A second config format would introduce precedence and repeat-run problems.

## Register through the supported client commands

Prefer the client CLI for scoped registration and check the effective registration before updating. This avoids rewriting a complete third-party user configuration file from the wizard. Support the current profile and its documented override. Treat a profile without an available CLI as detected but requiring manual registration. Verify command behavior on each supported OS in Phase 2. See [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) and [Claude Code MCP](https://code.claude.com/docs/en/mcp).

## Discover at supported locations and reuse importers

Search Codex `sessions` and Claude Code `projects` beneath their active roots, and inspect the configured ChatGPT export inbox if available. Let users add explicit local ChatGPT or Claude chat export paths. Agent snapshots are nested on disk and the existing importers accept individual files or flat directories. Enumerate compatible snapshot files under the supported roots and pass them through the existing source readers without changing document identity. Use the existing operator importer for each selected path, including ZIP archives. The separate acquisition command can resume a pending export from an earlier invocation, so calling it from setup could import a source the user did not select. Verify eligibility without processing unselected conversations, and skip symlink and junction traversal.
