# Installed Command and Release Contract

- Windows asset `engineering-memory-0.1.0-windows-x64-setup.exe`.
  Per-user payload under `%LOCALAPPDATA%\Programs\EngineeringMemory`.
- Ubuntu asset `engineering-memory_0.1.0_amd64.deb`.
  Payload under `/opt/engineering-memory` with command in `/usr/bin`.
- Each asset has a same-name `.sha256` sidecar with one SHA-256 and basename.
- Private config root is `%LOCALAPPDATA%\EngineeringMemory\config` or
  `${XDG_CONFIG_HOME:-$HOME/.config}/engineering-memory`. Store `app.env` and
  `compose.env` there. On Linux use mode 0700 for the root and 0600 for env
  files. On Windows use user-only profile ACLs with system access as required.
  Keep default durable host data under the per-user data location, outside
  the config and install roots, and document supported absolute overrides.
- `engineering-memory stack check` checks Compose, daemon access and required
  deployment settings. `stack start` starts services and waits for readiness.
  `stack stop` stops the project services with persistent volumes preserved.
  `stack status` reports service health. Unsuccessful operations exit nonzero
  with an actionable, sanitized diagnostic on stderr.
- Use stable Compose project `engineering-memory-workstation`. Publish
  Hindsight and any host-required proxy port on loopback only. Use the same
  project on every call and refer to bundled Compose files by absolute path.
- `--version`, `provision --json`, `import --export PATH --json`,
  `status --json` and `serve` retain their existing semantics. MCP clients
  launch the absolute installed executable with the single argument `serve`.
  Client configuration contains command and arguments, with secrets loaded
  from the workstation profile by the application.
