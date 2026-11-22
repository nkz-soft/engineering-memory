"""Inspect and update one read-only MCP registration in a current-user profile."""

import hashlib
import json
import os
import re
import stat
import tempfile
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import tomlkit
import typer
from tomlkit.exceptions import TOMLKitError
from tomlkit.items import InlineTable

from engineering_memory import setup_mcp_probe
from engineering_memory.ingestion.acquisition_lock import acquisition_lock
from engineering_memory.ingestion.acquisition_source import AcquisitionError
from engineering_memory.setup_client_discovery import Target, discover, group_targets
from engineering_memory.setup_profile import _private

SERVER = "engineering-memory"
PROFILE_RESOLUTION = "Open the client configuration UI to resolve its active profile, then retry."
_RESTART = "Restart the client and open a fresh session to check MCP tool availability."
_PROFILE = "Check that this user profile is readable, valid and not redirected, then retry."
_STALE = "The client profile changed. Scan again before editing it."
_SAVE = "Could not save the registration. Check profile access and retry."


@dataclass(frozen=True)
class Review:
    target: Target
    state: str
    token: str = ""
    diagnostic: str = ""


@dataclass(frozen=True)
class Registration:
    state: str
    diagnostic: str = ""
    probe: str = "skipped"


@dataclass(frozen=True)
class Snapshot:
    path: Path
    raw: bytes | None
    metadata: os.stat_result | None

    def token(self) -> str:
        digest = hashlib.sha256(os.path.normcase(os.path.normpath(self.path)).encode())
        if self.metadata is not None:
            metadata = self.metadata
            identity = (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_mtime_ns,
                metadata.st_ctime_ns,
                metadata.st_mode,
            )
            digest.update(str(identity).encode())
            digest.update(self.raw or b"")
        return digest.hexdigest()


def _safe_path(path: Path) -> None:
    if not path.is_absolute():
        raise ValueError("relative profile")
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError("redirected profile")


def _snapshot(path: Path) -> Snapshot:
    _safe_path(path)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return Snapshot(path, None, None)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise ValueError("invalid config file")
    contents = path.read_bytes()
    # Access time may legitimately change during the read.
    after = path.lstat()
    fields = ("st_dev", "st_ino", "st_mtime_ns", "st_ctime_ns", "st_size", "st_mode")
    if any(getattr(metadata, name) != getattr(after, name) for name in fields):
        raise ValueError("profile changed")
    _safe_path(path)
    return Snapshot(path, contents, metadata)


def _unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_json_constant(value):
    raise ValueError("non-JSON number")


def _document(snapshot: Snapshot):
    raw = (snapshot.raw or b"").decode("utf-8-sig")
    codex = snapshot.path.suffix.casefold() == ".toml"
    if codex:
        config = tomlkit.parse(raw)
        key = "mcp_servers"
    else:
        config = json.loads(
            raw if snapshot.raw is not None else "{}",
            object_pairs_hook=_unique_json,
            parse_constant=_invalid_json_constant,
        )
        key = "mcpServers"
    if not isinstance(config, Mapping) or not isinstance(config.get(key, {}), Mapping):
        raise ValueError("invalid MCP settings")
    return config, key


def _matches(entry, executable: Path) -> bool:
    if not isinstance(entry, Mapping):
        return False
    command = entry.get("command")
    if not isinstance(command, str) or not Path(command).is_absolute():
        return False
    return (
        entry.get("type", "stdio") == "stdio"
        and entry.get("enabled", True) is True
        and os.path.normcase(os.path.normpath(command))
        == os.path.normcase(os.path.normpath(executable))
        and entry.get("args") == ["serve"]
        and not any(
            entry.get(key)
            for key in (
                "env",
                "env_vars",
                "cwd",
                "url",
                "disabled_tools",
                "enabled_tools",
            )
        )
    )


def _diagnostic(config, target: Target) -> str:
    notices = dict.fromkeys(client.diagnostic for client in target.clients if client.diagnostic)
    if config.get("service_tier") == "default" and any(
        client.id == "codex-cli" for client in target.clients
    ):
        notices[
            'This Codex CLI may reject service_tier = "default". '
            "Use a compatible Codex version or correct the setting in Codex "
            "before checking its session."
        ] = None
    if any(client.id == "claude-code" for client in target.clients):
        projects = config.get("projects", {})
        if isinstance(projects, Mapping) and any(
            isinstance(project, Mapping)
            and isinstance(project.get("mcpServers"), Mapping)
            and SERVER in project["mcpServers"]
            for project in projects.values()
        ):
            notices["A Claude Code project has a local override. Check /mcp in that project."] = (
                None
            )
    return " ".join(notices)


def inspect(target: Target, executable: Path) -> Review:
    try:
        snapshot = _snapshot(target.config)
        config, key = _document(snapshot)
        servers = config.get(key, {})
        state = "absent"
        if SERVER in servers:
            state = "matching" if _matches(servers[SERVER], executable) else "conflict"
        return Review(target, state, snapshot.token(), _diagnostic(config, target))
    except (OSError, ValueError, TOMLKitError, RecursionError):
        return Review(target, "blocked", diagnostic=_PROFILE)


def _json_member(source: str, offset: int, name: str) -> tuple[int, int, str]:
    """Find a value span or an insertion point in an already validated JSON object."""
    decoder = json.JSONDecoder()
    skip_space = re.compile(r"[ \t\r\n]*").match
    cursor = skip_space(source, offset + 1).end()
    if source[cursor] == "}":
        return cursor, cursor, ""
    while True:
        key, end = decoder.raw_decode(source, cursor)
        colon = skip_space(source, end).end()
        start = skip_space(source, colon + 1).end()
        _, end = decoder.raw_decode(source, start)
        if key == name:
            return start, end, ""
        separator = skip_space(source, end).end()
        if source[separator] == "}":
            return end, end, ", "
        cursor = skip_space(source, separator + 1).end()


def _json_candidate(source: str, entry: dict) -> str:
    if not source:
        return json.dumps({"mcpServers": {SERVER: entry}}, ensure_ascii=False, indent=2) + "\n"
    config_start = len(source) - len(source.lstrip())
    start, end, separator = _json_member(source, config_start, "mcpServers")
    if start == end:
        new_member = json.dumps({"mcpServers": {SERVER: entry}}, ensure_ascii=False)[1:-1]
        return source[:start] + separator + new_member + source[end:]
    start, end, separator = _json_member(source, start, SERVER)
    value = json.dumps(entry, ensure_ascii=False)
    if start == end:
        value = separator + json.dumps(SERVER) + ": " + value
    return source[:start] + value + source[end:]


def _other_toml(source: str, had_servers: bool) -> dict:
    # A tagged token compares all TOML floats, including NaN, without losing precision.
    document = tomllib.loads(source, parse_float=lambda token: ("float", token))
    servers = document.get("mcp_servers", {})
    servers.pop(SERVER, None)
    if not had_servers:
        document.pop("mcp_servers", None)
    return document


def _toml_candidate(source: str, config, entry: dict) -> str:
    key = "mcp_servers"
    had_servers = key in config
    expected = _other_toml(source, had_servers)
    if not had_servers:
        config[key] = tomlkit.table(is_super_table=True)
    servers = config[key]
    replacement = tomlkit.inline_table() if isinstance(servers, InlineTable) else tomlkit.table()
    replacement.update(entry)
    servers[SERVER] = replacement
    candidate = tomlkit.dumps(config)
    try:
        if _other_toml(candidate, had_servers) == expected:
            return candidate
    except ValueError:
        pass

    # An inserted table header can capture later dotted keys. Put it after the original body.
    config = tomlkit.parse(source)
    if key in config and SERVER in config[key]:
        del config[key][SERVER]
    extra = tomlkit.document()
    extra.add(key, {SERVER: entry})
    candidate = tomlkit.dumps(config) + "\n" + tomlkit.dumps(extra)
    if _other_toml(candidate, had_servers) != expected:
        raise ValueError("unrelated TOML changed")
    return candidate


def _candidate(snapshot: Snapshot, executable: Path) -> bytes:
    source = (snapshot.raw or b"").decode("utf-8-sig")
    config, key = _document(snapshot)
    entry = {"command": str(executable), "args": ["serve"]}
    if key == "mcp_servers":
        contents = _toml_candidate(source, config, entry)
        if "\r\n" in source and "\n" not in source.replace("\r\n", ""):
            contents = contents.replace("\r\n", "\n").replace("\n", "\r\n")
        candidate = tomllib.loads(contents)
    else:
        if snapshot.path.name == ".claude.json":
            entry["type"] = "stdio"
        contents = _json_candidate(source, entry)
        candidate = json.loads(contents)
    if not _matches(candidate[key][SERVER], executable):
        raise ValueError("invalid updated registration")
    encoded = contents.encode()
    if snapshot.raw and snapshot.raw.startswith(b"\xef\xbb\xbf"):
        return b"\xef\xbb\xbf" + encoded
    return encoded


def _preserve_access(temporary: Path, snapshot: Snapshot) -> None:
    if os.name != "nt":
        if snapshot.metadata is not None:
            temporary.chmod(stat.S_IMODE(snapshot.metadata.st_mode))
        return

    import pywintypes
    import win32security

    try:
        if snapshot.metadata is None:
            _private(temporary)
            return
        descriptor = win32security.GetNamedSecurityInfo(
            str(snapshot.path),
            win32security.SE_FILE_OBJECT,
            win32security.DACL_SECURITY_INFORMATION,
        )
        protection = (
            win32security.PROTECTED_DACL_SECURITY_INFORMATION
            if descriptor.GetSecurityDescriptorControl()[0] & win32security.SE_DACL_PROTECTED
            else win32security.UNPROTECTED_DACL_SECURITY_INFORMATION
        )
        win32security.SetNamedSecurityInfo(
            str(temporary),
            win32security.SE_FILE_OBJECT,
            win32security.DACL_SECURITY_INFORMATION | protection,
            None,
            None,
            descriptor.GetSecurityDescriptorDacl(),
            None,
        )
    except pywintypes.error:
        raise OSError("could not preserve config permissions") from None


def _publish(temporary: Path, destination: Path, *, exists: bool) -> None:
    if exists:
        temporary.replace(destination)
    else:
        # An external writer may create the file after read-back. Publish without clobbering.
        if os.name == "nt":
            temporary.rename(destination)
        else:
            os.link(temporary, destination)


def _persist_if_current(snapshot: Snapshot, contents: bytes) -> bool:
    with tempfile.NamedTemporaryFile(dir=snapshot.path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            _preserve_access(temporary, snapshot)
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            if _snapshot(snapshot.path).token() != snapshot.token():
                return False
            _publish(temporary, snapshot.path, exists=snapshot.metadata is not None)
            return True
        finally:
            stream.close()
            temporary.unlink(missing_ok=True)


def persist(review: Review, executable: Path, *, replace: bool = False) -> Registration:
    if review.state == "blocked":
        return Registration("blocked", review.diagnostic)
    if review.state == "conflict" and not replace:
        return Registration("declined")
    if not executable.is_absolute():
        return Registration("blocked", "Use the absolute installed executable path.")

    path = review.target.config
    try:
        snapshot = _snapshot(path)
        if snapshot.token() != review.token:
            return Registration("blocked", _STALE)
        if review.state == "matching":
            # Verify the persisted file even when setup has nothing to write.
            return (
                Registration("already configured")
                if inspect(review.target, executable).state == "matching"
                else Registration("blocked", _STALE)
            )
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _safe_path(path)
        with acquisition_lock(path.with_name("." + path.name + ".engineering-memory")) as acquired:
            if not acquired or not _persist_if_current(snapshot, _candidate(snapshot, executable)):
                return Registration("blocked", _STALE)
            if inspect(review.target, executable).state != "matching":
                return Registration(
                    "failed", "The saved registration could not be verified. Scan again."
                )
        return Registration("saved")
    except (OSError, ValueError, TOMLKitError, AcquisitionError, RecursionError):
        return Registration("failed", _SAVE)


def verify(review: Review, executable: Path, *, replace: bool = False) -> Registration:
    saved = persist(review, executable, replace=replace)
    if saved.state not in {"saved", "already configured"}:
        return saved
    status = setup_mcp_probe.probe(executable)
    if status == "passed":
        return Registration(
            saved.state, " ".join(filter(None, (review.diagnostic, _RESTART))), status
        )
    reason = {
        "timeout": "The installed MCP server timed out.",
        "missing-tools": "The installed MCP server did not list both required tools.",
        "failed": "The installed MCP server could not complete initialization and tool listing.",
    }[status]
    return Registration(
        saved.state,
        " ".join(filter(None, (review.diagnostic, reason, "Rerun setup to retry."))),
        status,
    )


def configure(executable: Path) -> bool:
    clients = discover()
    if not clients:
        typer.echo("No supported client installations were found.")
    complete = True
    for client in clients:
        if client.config is None:
            tip = client.diagnostic or PROFILE_RESOLUTION
            typer.echo(f"{client.name}: {tip}")
            complete = False
    for target in group_targets(clients):
        names = ", ".join(client.name for client in target.clients)
        review = inspect(target, executable)
        typer.echo(f"{names}: {target.config} ({review.state}).")
        if review.diagnostic:
            typer.echo(review.diagnostic)
        if review.state == "blocked":
            complete = False
            continue
        if not typer.confirm(f"Set up {SERVER} for {names}?", default=False):
            continue
        replace = review.state == "conflict" and typer.confirm(
            f"Replace the existing {SERVER} registration for {names}?", default=False
        )
        result = verify(review, executable, replace=replace)
        summary = f"{names}: {result.state}. Local MCP check: {result.probe}."
        typer.echo(f"{summary} {result.diagnostic}".rstrip())
        complete &= result.state not in {"blocked", "failed"} and result.probe in {
            "passed",
            "skipped",
        }
    return complete
