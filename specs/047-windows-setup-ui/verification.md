# Verification

Verified on Windows 11 x64 on 2026-11-21 with Python 3.13.18, the locked release
dependencies and Inno Setup 6.5.4.

| Check | Result |
| --- | --- |
| Full pytest suite | `python -m pytest -q` in the repository's locked development environment reported 2,512 passed and 95 skipped. |
| Lint and format | `ruff check .` and `ruff format --check .` passed. |
| Windows package | The release PyInstaller recipe built the onedir payload. ISCC compiled `packaging/workstation/windows.iss` with AppVersion 0.1.0 and the bundled payload. |
| Packaged CLI | `python packaging/workstation/smoke.py <packaged executable> 0.1.0` verified the installed version, offline status, rejection of unattended terminal setup and read-only MCP tools. |
| Isolated installer fixture | The compiled post-install handlers ran against the bundled helper and a disposable per-user directory. Verified OpenRouter defaults, a Unicode path, Windows password masking, a save with startup unselected, saved-key redaction on reopen, deferral, silent reinstall profile preservation and a fresh silent install with no profile creation. A synthetic key was absent from the installer logs. |
| Compose rendering | A controlled Compose configuration check resolved the OpenRouter route to `openrouter/openai/gpt-oss-20b` and preserved a synthetic credential with special characters. |

The fixture used a separate app identity and skipped PATH and uninstaller
registration. The production installer compiled with SHA-256
`59946edbcb2eca932b9c56589d9c70db293ad68cd6ec8cd03f4680f6eaa2a711`.

The clean-VM interactive walkthrough, including keyboard and high DPI, and a
live stack start, bank provisioning and provider completion remain pending.
The validation host already had a workstation stack under the production
Compose project name. The installed fixture ran without starting that stack.
