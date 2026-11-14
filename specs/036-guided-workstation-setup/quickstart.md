# Clean-Workstation Validation

Use the candidate Windows x64 installer and Ubuntu amd64 package on clean supported workstations with compatible Docker and a test provider. Use disposable user profiles and synthetic history, including a known decision, a second unselected source and a malformed selection.

1. On Windows install as the signed-in user and select the guided setup option. On Ubuntu install with `sudo apt install ./engineering-memory_0.1.0_amd64.deb`, then run `engineering-memory setup` as the signed-in user. Accept defaults and complete provisioning without editing files. Confirm readiness with `engineering-memory stack status`.
2. Verify the private profile permissions and check terminal output, logs, client registrations and captured command arguments for a synthetic credential marker. Check ports and persistent paths with a second run.
3. Select both installed clients, then open fresh sessions and list the MCP servers with `codex mcp list` and `claude mcp list`. Confirm a pre-existing unrelated entry survives and each selected profile has one `engineering-memory` entry.
4. Select synthetic agent history and a local chat export. Exercise the typed-path option for one export. Confirm the outcome reports imported, skipped and failed items and the unselected source remains unimported. Use MCP to recall the known decision and open its sanitized conversation with `get_conversation`.
5. Reinstall and run setup again, accepting the existing settings. Re-select the same inputs and confirm unchanged imports are skipped, stable document IDs are retained and no duplicate registrations exist. Stop Docker or introduce a port conflict and confirm the wizard gives a retry action and performs zero imports.
6. Exercise silent installation on Windows and a noninteractive setup invocation on both platforms. Confirm the installer exits and setup reports the terminal requirement without prompting. Record command output and platforms with all sensitive values omitted.
