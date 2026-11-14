"""Register the read-only MCP server in selected current-user client profiles."""

import contextlib
import ctypes
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import typer

from engineering_memory import workstation
from engineering_memory.settings import (
    workstation_agent_profiles,
    workstation_subprocess_environment,
)
from engineering_memory.setup_profile import _atomic_write

SERVER = "engineering-memory"


@dataclass(frozen=True)
class Client:
    name: str
    cli: Path | None
    profile: Path


def profile_roots() -> dict[str, Path]:
    codex, claude, _ = workstation_agent_profiles()
    return {"Codex": codex, "Claude Code": claude}


def _find_cli(name: str) -> Path | None:
    # An explicit directory per lookup prevents Windows from implicitly probing CWD.
    for entry in os.get_exec_path():
        directory = Path(entry.strip('"'))
        if directory.is_absolute() and (cli := shutil.which(str(directory / name))):
            break
    else:
        return None
    path = Path(cli).absolute()
    if os.name != "nt" or path.suffix.lower() == ".exe":
        return path
    if name == "codex":
        # The npm package installs a native executable behind its shell shim.
        vendor = path.parent / "node_modules/@openai/codex/node_modules/@openai"
        return next(vendor.glob("codex-win32-*/vendor/*/codex/codex.exe"), None)
    return None


def discover() -> list[Client]:
    roots = profile_roots()
    candidates = [
        Client("Codex", _find_cli("codex"), roots["Codex"]),
        Client("Claude Code", _find_cli("claude"), roots["Claude Code"]),
    ]
    return [
        client
        for client in candidates
        if client.cli
        or client.profile.is_dir()
        or (client.name == "Claude Code" and workstation_agent_profiles()[2].is_file())
    ]


def _run(client: Client, *args: str) -> tuple[int, str]:
    environment = workstation_subprocess_environment()
    if client.name == "Codex":
        environment["CODEX_HOME"] = str(client.profile)
    if sys.platform == "win32" and workstation.is_installed():
        if not ctypes.windll.kernel32.SetDllDirectoryW(None):
            raise OSError("Cannot restore the native DLL search path")
    process = subprocess.run(
        [str(client.cli), *args],
        cwd=Path.home(),
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    return process.returncode, process.stdout


def _codex_current(client: Client) -> dict | None:
    status, output = _run(client, "mcp", "list", "--json")
    if status:
        raise ValueError("Cannot inspect the current registration")
    return next((item for item in json.loads(output) if item["name"] == SERVER), None)


def _claude_current(client: Client) -> tuple[Path, str | None, dict]:
    path = workstation_agent_profiles()[2]
    if path.is_symlink() or path.is_junction():
        raise ValueError("The Claude Code configuration is redirected")
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return path, None, {}
    config = json.loads(raw)
    if not isinstance(config, dict) or not isinstance(config.get("mcpServers", {}), dict):
        raise ValueError("Invalid user configuration")
    return path, raw, config


def _matches(entry: dict, executable: Path) -> bool:
    return (
        entry.get("type", "stdio") == "stdio"
        and os.path.normcase(os.path.normpath(entry.get("command", "")))
        == os.path.normcase(os.path.normpath(executable))
        and entry.get("args") == ["serve"]
        and not any(entry.get(key) for key in ("env", "env_vars", "cwd"))
    )


def _replace_allowed(client: Client) -> bool:
    return typer.confirm(
        f"Replace the existing {client.name} user registration for {SERVER}?", default=False
    )


def _register(client: Client, executable: Path) -> str:
    command = (str(executable), "serve")
    if client.name == "Codex":
        client.profile.mkdir(mode=0o700, parents=True, exist_ok=True)
        current = _codex_current(client)
        if current is not None:
            if current.get("enabled", True) and _matches(current.get("transport", {}), executable):
                return "already configured"
            if not _replace_allowed(client):
                return "kept existing registration"
            if _codex_current(client) != current:
                raise ValueError("The current registration changed")
        status, _ = _run(client, "mcp", "add", SERVER, "--", *command)
    else:
        path, previous, config = _claude_current(client)
        servers = config.get("mcpServers", {})
        if SERVER in servers:
            if _matches(servers[SERVER], executable):
                return "already configured"
            if not _replace_allowed(client):
                return "kept existing registration"
            if path.read_text(encoding="utf-8") != previous:
                raise ValueError("The current registration changed")
            # Replace one user entry atomically. Removing first would lose the previous target
            # if re-registration failed and restoring it via argv could expose its credentials.
            servers[SERVER] = {"type": "stdio", "command": command[0], "args": ["serve"]}
            _atomic_write(path, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
            return "configured"
        status, _ = _run(
            client, "mcp", "add", "--transport", "stdio", "--scope", "user", SERVER, "--", *command
        )
    if status:
        raise ValueError("The client rejected registration")
    return "configured"


def configure(executable: Path) -> bool:
    targets = discover()
    if not targets:
        typer.echo("No supported Codex or Claude Code profiles were found.")
    for client in targets:
        typer.echo(f"{client.name}: {client.profile}")
    complete = True
    for client in targets:
        if client.cli is None:
            typer.echo(f"{client.name}: use the workstation guide for manual MCP registration.")
            continue
        if not typer.confirm(f"Configure {client.name} for this user?", default=False):
            typer.echo(f"{client.name}: skipped by user.")
            continue
        outcome = None
        with contextlib.suppress(
            OSError, subprocess.SubprocessError, ValueError, TypeError, AttributeError, KeyError
        ):
            outcome = _register(client, executable)
        if outcome is None:
            typer.echo(
                f"{client.name}: registration failed. Check the user profile and retry.",
                err=True,
            )
            complete = False
        else:
            typer.echo(f"{client.name}: {outcome}.")
    return complete
