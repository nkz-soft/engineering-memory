# Verification: Inline MCP Setup Results on Windows

## Automated checks

Run the existing helper tests from the repository root.

```powershell
uv run pytest tests/unit/test_workstation_setup.py tests/unit/test_setup_clients.py
```

Use the Inno compiler pinned in `.github/workflows/release.yml` and an interactive Windows session for the compiled regression. The following script is a Phase 2 deliverable.

```powershell
& packaging/workstation/test-windows-mcp.ps1 -Compiler $compiler -Python $python -Scratch $scratch
```

Assert that the wizard returned from real progress after the first selected row and that both ordered apply requests reached the fixture helper. Repeat with first-row failure. Assert the Claude Desktop fixture write, untouched third profile, inline outcomes, retry and continue behavior. Exercise a declined conflict, confirmed conflict and a stale token after fixture mutation. Rerun the existing Windows maintenance matrix with the pinned compiler to check silent paths.

## Compiled installer with real client profiles

1. Use a disposable Windows user with Codex CLI / Desktop sharing a profile, Claude Desktop without an Engineering Memory entry, and another supported profile if available. Record only the relevant entry and local file hashes. Build the Windows installer using the existing release recipe, then run it interactively as that user.
2. In **Connect MCP clients**, select the matching Codex profile and the unconfigured Claude Desktop profile. Leave the third row unchecked. Run **Check selected clients**. Verify Codex is already configured, Claude Desktop is saved, both checks ran, and the unchecked profile is unchanged. Inspect the saved CLI command and `serve` argument locally.
3. Inspect the focused diagnostics and restart guidance, including the Codex CLI `service_tier` warning on a profile that has that setting. Restart the real clients and open a fresh session to confirm tool availability.
4. Repeat the two-client pass with controlled first-target failure in the disposable profile, such as changing its configuration after the scan so its token becomes stale. Confirm the next row still runs. Rescan, select only the intended retry target and check again. Verify **Next** can leave a failed row as displayed.
5. Repeat on identical-build configuration maintenance. Decline and accept a conflicting entry in separate runs. Verify only the confirmed entry changes, and check that settings confirmation still precedes writes. Report build identity, Windows version, outcome and any gaps. Keep config contents and credentials out of the report.
