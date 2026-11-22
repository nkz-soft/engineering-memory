"""Resolve current-user client installations to their user MCP files."""

import os
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from engineering_memory.settings import workstation_subprocess_environment

_CODEX_PACKAGE = "openai.codex_2p2nqsd0c76g0"
_CLAUDE_PACKAGE = "Claude_pzs8sxrjxfjjc"
_DESKTOP_CONFIG = "claude_desktop_config.json"
_DESKTOP_LOCATIONS = {"windowsapps", "claude-desktop", "chatgpt", "anthropicclaude", "claude-3p"}


@dataclass(frozen=True)
class Client:
    id: str
    name: str
    config: Path | None
    cli: Path | None = None
    diagnostic: str = ""


@dataclass(frozen=True)
class Target:
    config: Path
    clients: tuple[Client, ...]


def _absolute(value: str | None, home: Path, default: Path) -> Path:
    if value:
        path = Path(value.replace("~", str(home), 1) if value.startswith(("~/", "~\\")) else value)
        if path.is_absolute():
            return path
    return default


def _desktop_location(path: Path) -> bool:
    parts = {part.casefold() for part in path.parts}
    return bool(parts & _DESKTOP_LOCATIONS or {"claude", "claude-code"} <= parts)


def _cli(name: str, home: Path, environment: Mapping[str, str], local: Path) -> Path | None:
    windows = sys.platform == "win32"
    directories = [
        Path(entry.strip('"')) for entry in environment.get("PATH", "").split(os.pathsep)
    ]
    directories.append(home / ".local/bin")
    if windows and name == "codex":
        native = local / "Programs/OpenAI/Codex/bin"
        directories.extend((_absolute(environment.get("CODEX_INSTALL_DIR"), home, native), native))
    if windows:
        directories.append(
            _absolute(environment.get("APPDATA"), home, local.parent / "Roaming") / "npm"
        )
    for directory in directories:
        if not directory.is_absolute():
            continue
        # WindowsApps paths can refer to Desktop's aliases. A bundled Desktop CLI is not
        # independent installation evidence.
        if _desktop_location(directory):
            continue
        binary = directory / (name + ".exe" if windows else name)
        try:
            if (
                binary.is_file()
                and os.access(binary, os.X_OK)
                and not _desktop_location(binary.resolve())
            ):
                return binary
        except OSError:
            continue
        if not windows or not (directory / (name + ".cmd")).is_file():
            continue
        if name == "codex":
            package = directory / "node_modules/@openai/codex"
            native = "vendor/x86_64-pc-windows-msvc/codex/codex.exe"
            candidates = (
                package / "node_modules/@openai/codex-win32-x64" / native,
                package / native,
            )
        else:
            package = directory / "node_modules/@anthropic-ai/claude-code"
            # npm shims are installation evidence only when the official package is present.
            candidates = (package / "cli.js",)
        if candidate := next((path for path in candidates if path.is_file()), None):
            return candidate
    return None


def _windows_packages() -> set[str] | None:
    environment = workstation_subprocess_environment()
    powershell = (
        Path(environment.get("SYSTEMROOT", r"C:\Windows"))
        / "System32/WindowsPowerShell/v1.0/powershell.exe"
    )
    try:
        result = subprocess.run(
            [
                str(powershell),
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$ErrorActionPreference = 'Stop'; "
                "Get-AppxPackage -Name OpenAI.Codex | "
                "Select-Object -ExpandProperty PackageFamilyName; "
                "Get-AppxPackage -Name Claude | Select-Object -ExpandProperty PackageFamilyName",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return {line.strip().casefold() for line in result.stdout.splitlines()}


def _desktop_codex_home(home: Path, environment: Mapping[str, str]) -> Path:
    if sys.platform == "win32":
        import winreg

        # The Start menu launches Desktop with the persistent user environment. Shell-only
        # CODEX_HOME still applies to the CLI discovered from this invocation.
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value, _ = winreg.QueryValueEx(key, "CODEX_HOME")
        except OSError:
            value = None
        if isinstance(value, str):
            value = winreg.ExpandEnvironmentStrings(value)
    else:
        value = environment.get("CODEX_HOME")
    return _absolute(value, home, home / ".codex")


def _deb_installed(package: str, root: Path) -> bool:
    bin_path = f"/usr/bin/{package}"
    binary = root / bin_path.lstrip("/")
    if not binary.is_file() or not os.access(binary, os.X_OK):
        return False
    try:
        manifest = root / "var/lib/dpkg/info" / (package + ".list")
        return bin_path in manifest.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return False


def _claude_desktop_config(roaming: Path, mode: str = "") -> Path | None:
    standard, third_party = (roaming / name / _DESKTOP_CONFIG for name in ("Claude", "Claude-3p"))
    if mode == "1p":
        return standard
    if mode == "3p":
        return third_party
    if not third_party.parent.is_dir():
        return standard
    # Windows package migration leaves a placeholder even on a third-party-only profile.
    try:
        standard_active = standard.parent.is_dir() and any(
            not child.name.startswith(".user-data-left.") for child in standard.parent.iterdir()
        )
    except OSError:
        return None
    return None if standard_active else third_party


def _managed_notices(
    home: Path,
    environment: Mapping[str, str],
    root: Path,
) -> tuple[str, str]:
    if sys.platform == "win32":
        program_data = _absolute(environment.get("PROGRAMDATA"), home, Path(r"C:\ProgramData"))
        program_files = _absolute(environment.get("ProgramFiles"), home, Path(r"C:\Program Files"))
        codex_dir = program_data / "OpenAI/Codex"
        claude_dir = program_files / "ClaudeCode"
    else:
        codex_dir = root / "etc/codex"
        claude_dir = root / "etc/claude-code"

    codex = ""
    try:
        with (codex_dir / "requirements.toml").open("rb") as stream:
            if "mcp_servers" in tomllib.load(stream):
                codex = "A managed Codex policy controls MCP. Check whether it allows this server."
    except FileNotFoundError:
        pass
    except (OSError, ValueError):
        codex = "Could not inspect the managed Codex policy. Check MCP access in Codex."
    claude = ""
    if (claude_dir / "managed-mcp.json").is_file():
        claude = "A managed Claude Code policy overrides user MCP entries. Check with your admin."
    return codex, claude


def _claude_desktop_policy() -> tuple[str, str]:
    import winreg

    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, r"Software\Policies\Claude") as key:
                if winreg.QueryInfoKey(key)[1] == 0:
                    continue
                mode = _registry_value(key, "deploymentMode")
                disabled = _registry_value(key, "isLocalDevMcpEnabled") in (0, "0", "false")
        except OSError:
            continue
        notice = (
            "A managed Claude Desktop policy disables local MCP. Check with your admin."
            if disabled
            else ""
        )
        return mode if mode in ("1p", "3p") else "", notice
    return "", ""


def _registry_value(key, name: str):
    import winreg

    try:
        return winreg.QueryValueEx(key, name)[0]
    except FileNotFoundError:
        return None


def discover(
    *,
    home: Path | None = None,
    environment: Mapping[str, str] | None = None,
    system_root: Path = Path("/"),
    windows_packages: Callable[[], set[str] | None] | None = None,
    desktop_codex_home: Path | None = None,
    desktop_claude_mode: str = "",
) -> tuple[Client, ...]:
    if sys.platform not in {"win32", "linux"}:
        return ()
    home = Path.home() if home is None else home
    native_environment = environment is None
    environment = workstation_subprocess_environment() if environment is None else environment
    local = _absolute(environment.get("LOCALAPPDATA"), home, home / "AppData/Local")
    codex_home = _absolute(environment.get("CODEX_HOME"), home, home / ".codex")
    claude_home = _absolute(environment.get("CLAUDE_CONFIG_DIR"), home, home)
    clients = []
    codex_notice, claude_notice = _managed_notices(home, environment, system_root)
    if codex := _cli("codex", home, environment, local):
        clients.append(
            Client("codex-cli", "Codex CLI", codex_home / "config.toml", codex, codex_notice)
        )
    if claude := _cli("claude", home, environment, local):
        clients.append(
            Client(
                "claude-code", "Claude Code", claude_home / ".claude.json", claude, claude_notice
            )
        )

    if sys.platform == "win32":
        installed_packages = (windows_packages or _windows_packages)()
        packages = {name.casefold() for name in installed_packages or ()}
        codex_desktop = _CODEX_PACKAGE in packages
        if native_environment:
            desktop_claude_mode, desktop_notice = _claude_desktop_policy()
        else:
            desktop_notice = ""
        if _CLAUDE_PACKAGE.casefold() in packages:
            clients.append(
                Client(
                    "claude-desktop",
                    "Claude Desktop",
                    _claude_desktop_config(
                        local / "Packages" / _CLAUDE_PACKAGE / "LocalCache/Roaming",
                        desktop_claude_mode,
                    ),
                    diagnostic=desktop_notice,
                )
            )
        elif installed_packages is not None and any(
            (local / name).is_file()
            for name in (
                "AnthropicClaude/Claude.exe",
                "Programs/Claude/Claude.exe",
            )
        ):
            roaming = _absolute(environment.get("APPDATA"), home, home / "AppData/Roaming")
            clients.append(
                Client(
                    "claude-desktop",
                    "Claude Desktop",
                    _claude_desktop_config(roaming, desktop_claude_mode),
                    diagnostic=desktop_notice,
                )
            )
    else:
        codex_desktop = _deb_installed("chatgpt", system_root)
        if _deb_installed("claude-desktop", system_root):
            xdg = _absolute(environment.get("XDG_CONFIG_HOME"), home, home / ".config")
            clients.append(Client("claude-desktop", "Claude Desktop", _claude_desktop_config(xdg)))

    if codex_desktop:
        if desktop_codex_home is None:
            desktop_codex_home = (
                _desktop_codex_home(home, environment) if native_environment else codex_home
            )
        clients.append(
            Client(
                "codex-desktop",
                "Codex Desktop",
                desktop_codex_home / "config.toml",
                diagnostic=codex_notice,
            )
        )
    if sys.platform == "win32" and installed_packages is None:
        clients.append(
            Client(
                "desktop-discovery-unavailable",
                "Windows packaged clients",
                None,
                diagnostic="Could not query Windows packages. Retry from your user session.",
            )
        )
    return tuple(clients)


def group_targets(clients: tuple[Client, ...]) -> tuple[Target, ...]:
    grouped: dict[str, list[Client]] = {}
    for client in clients:
        if client.config is not None:
            # Normalize lexical aliases and Windows case without following reparse points.
            identity = os.path.normcase(os.path.normpath(client.config))
            grouped.setdefault(identity, []).append(client)
    return tuple(Target(members[0].config, tuple(members)) for members in grouped.values())
