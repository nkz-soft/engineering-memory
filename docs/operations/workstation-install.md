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

After copying files, the installer opens **Configure Engineering Memory**.
A fresh profile starts with OpenRouter, model `openai/gpt-oss-20b` and API base
`https://openrouter.ai/api/v1`. Edit the provider, model, API base, ports and
data paths as needed. Enter your API key in the masked field. The wizard loads
saved settings and retains outbound proxy settings. Leave the key
blank to keep it for the saved provider, or enter a replacement.

Select **Save** or **Configure later**, then choose which profiles to register
on **Connect MCP clients**. If you saved provider settings, the next page
offers to start the local stack and provision the shared bank. Start Docker
before selecting this option. If setup fails, retry from the installer or
finish and continue later.

#### Rerun the Windows installer

Setup checks the installation for your Windows account before it copies files.

| What Setup finds | What you can do |
| --- | --- |
| Same version and build | Open the existing settings and MCP pages or exit. No application files are copied. Review both pages and confirm **Apply** to save settings or change selected MCP registrations. Cancelling before confirmation leaves both unchanged. |
| Newer version | Review the installed and incoming versions and accept an in-place update. |
| Different build at the same version | Review the two build identifiers and explicitly accept replacement. |
| Older package | Close Setup and obtain the installed version or a newer verified package. |
| Missing or damaged files, or a legacy installation without a build identity | Use **Repair the installation** with a verified package of the same or a newer version when Setup can establish the installed version. If Setup cannot establish the version or location, check the installed entry and verify the package before retrying. |

Updating or repairing keeps the private profile, credentials, ports, proxy
settings, archive, SQLite state, Docker volume and unrelated MCP registrations.
On the optional setup pages, choose **Configure later** and leave MCP targets
unselected to keep the current profile. When Setup reports files in use, close
the running Engineering Memory processes and retry.

`/SILENT` and `/VERYSILENT` install a fresh payload or update a verified healthy
installation to a strictly newer version. An identical healthy package exits
successfully without changing files or settings. Older packages, same-version
replacements, and repair or uncertain states exit with a nonzero status. Silent
runs skip configuration, MCP registration and service startup. Add
`/SUPPRESSMSGBOXES /NORESTART /LOG="<absolute log path>"` for unattended use and
look for `EM-MAINTENANCE` in the installer log when a run is blocked. Use the
maintained installer for these checks. Earlier installer builds did not implement
the version guard.

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

## Verify and manage the installation

On Ubuntu, the terminal wizard checks Docker before prompting for provider
settings. Client registration is offered even when startup is deferred.
History import is offered after the shared bank is ready.

After completing setup and opting in to startup, open a new terminal and check
the installed version and service state. On Windows, a new terminal also picks
up the updated user PATH.

```text
engineering-memory --version
engineering-memory stack status
```

Expect `engineering-memory 0.0.1` and healthy services. Use
`engineering-memory stack stop` to stop the services and
`engineering-memory stack start` to start them again. To resume deferred setup,
update an existing profile, edit outbound proxies, register coding agents or
import history, run:

```text
engineering-memory setup
```

Review the detected histories before selecting any to import. For a local
ChatGPT or Claude export outside the configured inbox, enter its path when
prompted. Reinstalling preserves the profile and data.

### Outbound proxy for the LLM provider

Use **Custom provider API base** for the address of an OpenAI-compatible
provider, such as `https://provider.example/v1`. Use **Outbound proxy for HTTP
destinations** or **Outbound proxy for HTTPS destinations** for the network
forward proxy that LiteLLM uses to reach that provider.

Enter a proxy URL in the form `http://host:port` or `https://host:port`. Choose
the field by the provider URL's scheme. For example, enter
`http://host.docker.internal:3128` in the HTTPS destination field to reach an
HTTPS provider through a host-based HTTP proxy using CONNECT. The proxy must
listen on an address reachable from Docker and allow connections from the
container. A proxy bound only to the host's loopback may be unreachable. Inside
LiteLLM, `localhost` refers to the container. Use an HTTPS proxy URL when the
proxy itself accepts TLS and its certificate is trusted by LiteLLM.

For an authenticated proxy, use `http://username:password@host:port` and
percent-encode reserved characters in the username and password. The wizard
hides the URL input and saves it with the existing private Compose settings.
While the profile manages routing, the bypass always includes `localhost`,
`127.0.0.1`, `::1`, `hindsight` and `litellm`. Enter additional hosts as a
comma-separated list if LiteLLM should reach them directly.

Rerun `engineering-memory setup` and select **set** to change a URL or **clear**
to remove it. Enter a single hyphen to clear additional bypass hosts. Save and
start the stack from setup, or run `engineering-memory stack start` afterward.
Clearing both URLs and the additional bypass restores the base Docker behavior,
including any proxy defaults configured separately in Docker. The wizard
controls LiteLLM's provider route. Docker daemon access and image pulls use
Docker's own settings.

When a URL is configured, setup offers to send one synthetic completion to
check the provider route. This may incur one provider request. If it fails,
check container reachability, proxy authentication or access policy, and the
provider settings before retrying.

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

On Windows and Ubuntu, interactive installation offers the native Codex CLI,
Codex Desktop, Claude Code and Claude Desktop installed for your account.
Ubuntu coverage includes the vendor Desktop preview and beta. Select each
profile you want to configure. A common Codex CLI and Desktop configuration
is shown once. The Windows wizard recognizes packaged Claude Desktop profiles,
including `Claude-3p`.

The installer adds the absolute installed Engineering Memory executable and
the argument `serve`. A matching entry is kept. If the existing entry points
to a checkout or another server, review and confirm before replacing it.
When Codex CLI rejects `service_tier = "default"`, use a compatible Codex
version or correct the setting in Codex before checking a fresh session.
Setup preserves that setting. If a profile is ambiguous, check the active
configuration in the client and retry `engineering-memory setup`.

A passed local MCP check means the installed executable completed
`initialize` and listed `search_memory` and `get_conversation`. It uses a
temporary offline profile. To verify your client, fully quit and relaunch
Desktop, or start a new CLI session. Check `/mcp` in Codex or Claude Code and
the Chat connector picker or local MCP settings in Claude Desktop. If a
profile was saved but the local check failed, rerun setup and check the
reported diagnostic. If tools are missing only in a new session, check the
client's active profile and managed settings.

To keep coding-agent history current, configure
[automatic session import](session-import.md) and optionally schedule it
under the same user account.

## Maintainer release procedure

Each PR build uploads versioned packages, the Ubuntu launcher, checksum
sidecars and a `BUILD-COMMIT` file for the exact revision. After merge, tag the approved commit `v0.0.1` and push the tag. The same workflow uses the
locked uv environment and pinned Python and Inno Setup versions, checks the
installed version on both platforms, and creates a draft release with the
packages, launcher, checksums and installation notes. To reproduce the payload locally,
run `uv sync --locked --no-dev --group release` followed by
`uv run --no-sync python packaging/workstation/build.py v0.0.1 build/payload`
on native x64. On Ubuntu run `bash packaging/workstation/build-deb.sh
build/payload/engineering-memory build/assets 0.0.1`. On Windows compile
`packaging/workstation/windows.iss` with Inno Setup 6.5.4, defining
`AppVersion=0.0.1`, `Payload=<absolute path to build/payload/engineering-memory>`,
and `BuildIdentity=<lowercase SHA-256 of engineering-memory.build in that payload>`
with ISCC's `/D` options. The Windows payload build generates the manifest. The
installer uses its hash as the build identity, independently of the release
version.

Download the exact draft assets and record both passes of the
[clean-workstation acceptance guide](../../specs/045-workstation-release/quickstart.md).
Publish the draft only after both passes, then re-download the public assets
and compare them to the published sidecars.
