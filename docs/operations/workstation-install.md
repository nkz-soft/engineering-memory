# Install Engineering Memory on a workstation

Use the release installer for Windows 11 x64 or Ubuntu 24.04 LTS amd64. The
installer supplies the `engineering-memory` command, its Python runtime and local
deployment files. Install Docker Desktop in Linux-container mode on Windows or
Docker Engine with the Compose plugin on Ubuntu. Start Docker and ensure your
account can use it. Use Docker Engine 28 or newer for loopback-only published ports and Compose
2.24.4 or newer. You also need an LLM
provider and credentials that LiteLLM can use.

## Download and install

Download the platform files and their SHA-256 sidecars from
[version 0.0.1](https://github.com/nkz-soft/engineering-memory/releases/tag/v0.0.1).

### Windows 11 x64

From the download folder, compare the PowerShell hash with the first field of
the checksum sidecar.

```powershell
Get-FileHash -Algorithm SHA256 .\engineering-memory-0.0.1-windows-x64-setup.exe
Get-Content .\engineering-memory-0.0.1-windows-x64-setup.exe.sha256
```

If the hashes match, run the installer as your own user.

```powershell
.\engineering-memory-0.0.1-windows-x64-setup.exe
```

Leave **Run Engineering Memory guided setup** selected on the final screen.
When you finish the installation, the wizard opens automatically. Silent
installation only places the CLI and runtime.

### Ubuntu 24.04 LTS amd64

Download the launcher, the `.deb` and both sidecars into the same directory
under your user account. Use a directory that only your account can modify.
From an interactive terminal in that directory, run:

```bash
sha256sum -c engineering-memory-0.0.1-ubuntu-amd64-install.sh.sha256
sha256sum -c engineering-memory_0.0.1_amd64.deb.sha256
```

If both checks report `OK`, start the launcher as your own user.

```bash
bash engineering-memory-0.0.1-ubuntu-amd64-install.sh ./engineering-memory_0.0.1_amd64.deb
```

Authorize apt when prompted for sudo. The launcher then starts guided setup
in the same terminal using your account. If a development build with a higher
version is present, use a clean workstation or review it in apt before retrying.

## Guided setup

Enter your model identifier and provider credentials when prompted. The wizard
checks Docker, starts the local services and provisions the shared bank.
Wait for `Shared memory bank provisioned.` The wizard then offers optional
MCP registration and history import. Review the detected histories before
selecting any to import. For a local ChatGPT or Claude export outside the
configured inbox, enter its path when prompted.

Open a new terminal from any directory, so Windows picks up the updated user
PATH, then check the installed version and service state.

```text
engineering-memory --version
engineering-memory stack status
```

Expect `engineering-memory 0.0.1` and running, healthy services. Use
`engineering-memory stack stop` to stop the services and
`engineering-memory stack start` to start them again. If setup fails or you
defer it, resolve the reported problem and rerun the installer. You can also
resume an installed profile with `engineering-memory setup`. Reinstalling
preserves the profile and data.

## Manual setup

Copy `app.env.example` to `app.env` and `compose.env.example` to `compose.env`
within your private configuration directory. Do this once and keep those files
when reinstalling. The examples are under `_internal/deploy/workstation` in
the installed payload.

| Platform | Installed payload | Private configuration | Default data |
| --- | --- | --- | --- |
| Windows | `%LOCALAPPDATA%\Programs\EngineeringMemory` | `%LOCALAPPDATA%\EngineeringMemory\config` | `%LOCALAPPDATA%\EngineeringMemory\data` |
| Ubuntu | `/opt/engineering-memory` | `${XDG_CONFIG_HOME:-$HOME/.config}/engineering-memory` | `${XDG_DATA_HOME:-$HOME/.local/share}/engineering-memory` |

On Ubuntu set directory permissions to `0700` and file permissions to `0600`
before entering credentials. On Windows keep them in your own Local AppData
directory and verify that the config folder's ACL grants access only to your
account and the system or administrators as required by your machine.

Set `PRODUCT_PROVIDER_MODEL` to a LiteLLM provider/model identifier and
`PRODUCT_PROVIDER_API_KEY` to your real credential in `compose.env`. For a
custom OpenAI-compatible endpoint, set `PRODUCT_PROVIDER_API_BASE` to the
container-reachable API base URL. Set `WORKSTATION_PROXY_KEY` to a newly generated
local value beginning with `sk-`, then put the same value in
`ENGINEERING_MEMORY_LLM__API_KEY` in `app.env`. Docker publishes Hindsight
and the proxy on loopback. If ports 8888 or 4000 are occupied, change the
corresponding port in both files. Use absolute paths for optional archive or
SQLite overrides. Keep those paths outside the installation directory.

```text
engineering-memory stack check
engineering-memory stack start
engineering-memory stack status
engineering-memory provision --json
engineering-memory import --export "<absolute export path>" --json
engineering-memory status --json
engineering-memory stack stop
```

The stack status reports service state. Plain status reads local import state
offline. The first start pulls backend images. If it fails, check Docker
availability, port conflicts and provider settings, then retry. Start the
stack again before using MCP. Stop preserves the Hindsight volume, and
rerunning the installer preserves the private configuration and local data.

## Coding-agent setup

Give the client the absolute installed command path and the single argument
`serve`. Resolve the actual Windows path with
`(Get-Command engineering-memory).Source` or use
`/usr/bin/engineering-memory` on Ubuntu. In the commands below, substitute
that path and quote it if it contains spaces.

```text
codex mcp add engineering-memory -- "<absolute installed executable>" serve
claude mcp add --transport stdio --scope user engineering-memory -- "<absolute installed executable>" serve
```

Start a fresh client session. Ask it to use Engineering Memory to find an
imported decision and open the matching conversation with `get_conversation`.
The MCP server reads the same local configuration when launched from any
working directory.

To keep coding-agent history current, configure
[automatic session import](session-import.md) and optionally schedule it
under the same user account.

## Maintainer release procedure

Each PR build uploads versioned packages, the Ubuntu launcher and checksum
sidecars. After merge, tag the approved commit `v0.0.1` and push the tag. The same workflow uses the
locked uv environment and pinned Python and Inno Setup versions, checks the
installed version on both platforms, and creates a draft release with the
packages, launcher, checksums and installation notes. To reproduce the payload locally,
run `uv sync --locked --no-dev --group release` followed by
`uv run --no-sync python packaging/workstation/build.py v0.0.1 build/payload`
on native x64. On Ubuntu run `bash packaging/workstation/build-deb.sh
build/payload/engineering-memory build/assets 0.0.1`. On Windows compile
`packaging/workstation/windows.iss` with Inno Setup 6.5.4, defining
`AppVersion=0.0.1` and `Payload=<absolute path to build/payload/engineering-memory>`
with ISCC's `/D` options.

Download the exact draft assets and record both passes of the
[clean-workstation acceptance guide](../../specs/045-workstation-release/quickstart.md).
Publish the draft only after both passes, then re-download the public assets
and compare them to the published sidecars.
