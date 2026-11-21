# Candidate Workstation Acceptance

This is the validation procedure for the planned release. Record actual outcomes when the artifacts are available.

1. Prepare clean Windows 11 x64 and Ubuntu 24.04 LTS amd64 user profiles with the documented Docker versions and a compatible test provider. Use only synthetic histories. Record OS, Docker and Compose versions, candidate tag and commit.
2. Download the exact draft assets and sidecars. Verify SHA-256 with `Get-FileHash -Algorithm SHA256` on Windows and `sha256sum -c` on Ubuntu. Record all applicable digests.
3. Use the single entry point in the [installer contract](contracts/install.md). On Windows, verify the embedded page opens as the signed-in user, enter provider settings, save and opt in to startup and bank provisioning. On Ubuntu, verify the launcher opens terminal setup as the signed-in user, enter provider settings, confirm startup and decline optional registration and import for this pass. Confirm both services report ready and the shared bank was provisioned without separate lifecycle commands.
4. Open a fresh terminal outside the installation directory. Run `engineering-memory --version` and `engineering-memory stack status`. Import a synthetic export with `engineering-memory import --export "<absolute fixture path>" --json`. Use an installed stdio MCP session to verify search, retrieval, stable identity, original time and sanitized context.
5. Exercise stop/start and reinstall the same installer. Confirm persisted configuration, archive, SQLite state and backend data. Repeat the unchanged import and verify it skips, then retrieve the same conversation through MCP.
6. Stop Docker or trigger a controlled failure. Confirm the setup explains the failed step, does not claim readiness or import data, and allows retry after the issue is cleared. Verify logs and published evidence lack credential values.
7. Publish only after both records pass. Re-download all public assets and verify their hashes against the accepted candidate records. Run the separate [#71](https://github.com/nkz-soft/engineering-memory/issues/71) manual real-agent scenario after installation.
