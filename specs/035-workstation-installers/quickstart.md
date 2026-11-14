# Clean Workstation Acceptance

Run on Windows 11 x64 and Ubuntu 24.04 LTS amd64 with a fresh user profile, Docker
and a compatible provider. Do not install Python or uv or clone the repository
on the target. Stage a synthetic ChatGPT export with a known decision and
source timestamp. Keep the decision out of the agent prompt.

1. Download the installer and matching sidecar. On Windows run
   `Get-FileHash -Algorithm SHA256 .\engineering-memory-0.1.0-windows-x64-setup.exe`
   and compare its hash to the sidecar. On Ubuntu run
   `sha256sum -c engineering-memory_0.1.0_amd64.deb.sha256`.
2. Run the Windows installer as the current user or
   `sudo apt install ./engineering-memory_0.1.0_amd64.deb`. Open a fresh
   terminal from outside the install directory and run
   `engineering-memory --version`. Expect `engineering-memory 0.1.0`.
3. Follow the installed profile guide for Docker, the provider and absolute
   paths. Run `engineering-memory stack check`, `stack start` and
   `stack status` using the installed command. Expect a ready backend.
4. Run `engineering-memory provision --json`, then
   `engineering-memory import --export "<absolute fixture path>" --json`.
   Confirm successful provisioning and one imported fixture.
5. Register the installed executable and `serve` in Codex or Claude Code.
   In a fresh client process from a different working directory, ask it to
   find the decision and open the matching conversation through
   `get_conversation`. Check its content, stable ID and original date.
6. Stop and restart the stack. Repeat the fresh-client check and confirm
   `engineering-memory status --json` still sees the recorded import.
7. Stop the stack, rerun the same installer, start it again and repeat the
   checks. Compare private configuration and archive file hashes locally,
   verify the existing SQLite records, and run the same import again.
   Expect a skip and the same recall result and openable source.
8. Record OS, Compose version, tag/commit, installer digest, and pass/fail
   for each step. Once the release is public, verify hashes against both
   public downloads. Keep all test credentials out of published evidence.
