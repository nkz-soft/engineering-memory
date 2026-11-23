# Contract: Windows Installer Maintenance

| Observed current-user state | Interactive outcome | `/SILENT` and `/VERYSILENT` |
| --- | --- | --- |
| No installation evidence | Normal install and existing wizard | Install payload only, success |
| Healthy, equal version and build | Open existing configuration or exit | Success with no persistent product changes |
| Healthy, incoming version strictly newer | Show both versions and offer in-place update | Update payload only, success after verification |
| Healthy, equal version and different build | Show both identities or distinguishable prefixes and request replacement | Block, nonzero |
| Reliable installed version newer than incoming | Block and direct the operator to a current package | Block, nonzero |
| Incomplete, valid non-older incoming version | Explain the problem and offer explicit repair | Block, nonzero |
| Incomplete, ordering cannot be established | Explain how to obtain a suitable artifact and verify or recover the installed state before retrying | Block, nonzero |

A normal Inno log may report a fixed outcome and safe reason. Document running with `/LOG` and `/SUPPRESSMSGBOXES` for unattended callers. Logs omit runtime settings, keys, history and client data. Every blocked result prevents payload writes and helper calls.

## Maintenance configuration

Use the current settings status and MCP target confirmation flow. Read existing settings and inspect MCP targets only through the existing helper on a healthy installed build in a regular user session. Hold edits, registration selections and conflict confirmations until the final explicit apply action. Exit, Back or Cancel before that action performs no write. At apply time, retain existing stale-input protection and report success or errors by stage or target, so a retry can work from the newly observed state.

The silent no-op and interactive exit leave application files, uninstaller files, uninstall registration and PATH untouched and do not stop or start services. Configuration changes only the selected fields or registrations and does not start the stack. Fresh installs and accepted payload operations preserve the regular post-install configuration and startup choices. The installer must provide recovery guidance if it cannot verify a complete installed build.
