# Validation and Operator Checklist

## Automated acceptance after implementation

1. Run `uv run --locked pytest -q tests/unit/test_setup_client_discovery.py tests/unit/test_setup_clients.py tests/unit/test_setup_mcp_probe.py tests/unit/test_workstation_setup.py tests/structure/test_ubuntu_installer.py`. Confirm the dedicated PR check completes on both runner targets and the required GitHub check covers both results.
2. Run the normal Windows and Ubuntu packaging and installed smoke steps documented in [release.yml](../../.github/workflows/release.yml). Exercise a compiled Windows wizard fixture and the Ubuntu launcher under isolated regular-user homes. Save PR run URL, exact Git SHA, platform files and SHA-256 sidecars and `BUILD-COMMIT`. Use a review build with no public release tag.
3. Compare `BUILD-COMMIT` with the implementation commit. Compare each file against the manifest with `Get-FileHash -Algorithm SHA256 <installer>` on Windows or `sha256sum -c ./*.sha256` on Ubuntu. Run the normal interactive installer or launcher with the accompanying verified package.

## Fresh-session checklist

Use a disposable account or test VM where needed for Desktop-only, custom and conflicting cases. Record installer SHA, client version, platform, expected profile type, installer result and actual tool visibility.

- [ ] Run the standard interactive installer with a supported Desktop installation and its vendor's CLI absent. On Windows, cover both desktop apps and include the packaged `Claude-3p` case. On Ubuntu, exercise both vendor preview/beta Desktop packages. Confirm the built-in Windows page or Ubuntu guided setup offers the expected client before completion.
- [ ] Select an absent entry and check that the persisted command points to the installed executable with `serve`. On shared Codex CLI/Desktop, check one entry and both client results. Rerun and check that a match is unchanged.
- [ ] Seed a disposable profile with a source-checkout registration and unrelated settings/server entries. Decline replacement and compare the original file. Retry, confirm replacement and compare everything outside that entry. For the Windows npm Codex compatibility case, preserve `service_tier = "default"` and record the diagnostic. Use a compatible profile for the separate fresh-session tool check.
- [ ] Confirm the installer reports the saved registration and local handshake independently. With a no-client profile and on a silent Windows install, check that no client config is created or edited.
- [ ] Fully exit each desktop app, including its tray process, and relaunch. Start new CLI sessions. For Codex CLI and Desktop open `/mcp` or the MCP settings/status view. For Claude Code use `/mcp`. For Claude Desktop use the Chat connector/tool picker or the local MCP server status under Settings. Record whether both `search_memory` and `get_conversation` are advertised for `engineering-memory` in each fresh session. Keep retrieval scenarios in #71.
