"""Collect and persist the private workstation profile."""

import json
import os
import re
import secrets
import tempfile
from io import StringIO
from pathlib import Path
from urllib.parse import urlsplit

import typer

from engineering_memory import workstation
from engineering_memory.ingestion.acquisition_lock import acquisition_lock
from engineering_memory.ingestion.acquisition_source import AcquisitionError
from engineering_memory.settings import workstation_dotenv, workstation_dotenv_entries


class ProfileError(RuntimeError):
    """A safe message about profile configuration."""


def _private(path: Path, *, directory: bool = False) -> None:
    if os.name == "nt":
        from pywintypes import error as WindowsError

        try:
            _apply_private_mode(path, directory=directory)
        except WindowsError:
            raise OSError("Cannot protect the private file or directory") from None
    else:
        _apply_private_mode(path, directory=directory)


def _apply_private_mode(path: Path, *, directory: bool) -> None:
    if path.is_symlink() or path.is_junction():
        raise ProfileError("The private profile contains a redirected path. Check its location.")
    if os.name != "nt":
        if path.stat().st_uid != os.getuid():
            raise ProfileError("The private profile must belong to the installing user.")
        path.chmod(0o700 if directory else 0o600)
        return

    import ntsecuritycon
    import win32api
    import win32con
    import win32security

    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        user, _ = win32security.GetTokenInformation(token, win32security.TokenUser)
    finally:
        token.Close()
    acl = win32security.ACL()
    flags = win32con.OBJECT_INHERIT_ACE | win32con.CONTAINER_INHERIT_ACE if directory else 0
    for sid in (
        user,
        win32security.CreateWellKnownSid(win32security.WinLocalSystemSid, None),
        win32security.CreateWellKnownSid(win32security.WinBuiltinAdministratorsSid, None),
    ):
        acl.AddAccessAllowedAceEx(
            win32security.ACL_REVISION, flags, ntsecuritycon.FILE_ALL_ACCESS, sid
        )
    win32security.SetNamedSecurityInfo(
        str(path),
        win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
        None,
        None,
        acl,
        None,
    )


def _atomic_write(path: Path, contents: str) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            _private(temporary)
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            if os.name == "nt":
                from engineering_memory.archive._windows import publish

                publish(temporary, path)
            else:
                temporary.replace(path)
                _sync_directory(path.parent)
        finally:
            stream.close()
            temporary.unlink(missing_ok=True)


def _sync_directory(path: Path) -> None:
    if os.name != "nt":
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _restore(journal: Path, files: tuple[Path, Path]) -> None:
    old = json.loads(journal.read_text(encoding="utf-8"))
    if (
        not isinstance(old, list)
        or len(old) != len(files)
        or not all(value is None or isinstance(value, str) for value in old)
    ):
        raise ProfileError("The profile recovery file is invalid. Restore your profile backup.")
    for path, previous in zip(files, old, strict=True):
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            _atomic_write(path, previous)
    journal.unlink()
    _sync_directory(journal.parent)


def _compose_values(path: Path) -> dict[str, str | None]:
    if not path.exists():
        return {}
    values = {}
    with path.open(encoding="utf-8") as stream:
        for binding in workstation_dotenv_entries(stream):
            if binding.key is None:
                continue
            raw = binding.original.string.partition("=")[2].lstrip()
            value = binding.value
            if raw.startswith("'"):
                # Compose preserves literal backslashes inside single quotes except for \'
                # (unlike python-dotenv, which also decodes \\).
                match = re.match(r"'((?:\\'|[^'])*)'", raw)
                if match:
                    value = match[1].replace("\\'", "'")
            elif value is not None and raw.startswith('"'):
                value = value.replace("$$", "$")
            values[binding.key] = value
    return values


def _replace_settings(text: str | None, values: dict[str, str], *, compose: bool = False) -> str:
    text = "".join(
        entry.original.string
        for entry in workstation_dotenv_entries(StringIO(text or ""))
        if entry.key not in values
    )
    lines = []
    for key, value in values.items():
        if compose:
            literal = json.dumps(value, ensure_ascii=False).replace("$", "$$")
        else:
            escaped = value.replace("\\", "\\\\").replace("'", "\\'")
            literal = f"'{escaped}'"
        lines.append(f"{key}={literal}")
    separator = "" if not text or text.endswith("\n") else "\n"
    return text + separator + "\n".join(lines) + "\n"


def _prompt(label: str, default: str, valid, *, secret: bool = False) -> str:
    while True:
        value = typer.prompt(
            label,
            default="" if secret else default,
            show_default=not secret and bool(default),
            hide_input=secret,
        )
        value = value or default if secret else value
        if not any(ord(char) < 32 or ord(char) == 127 for char in value) and valid(value):
            return value
        typer.echo(f"Invalid {label.lower()}. Enter a valid value.", err=True)


def _valid_url(value: str) -> bool:
    if not value:
        return True
    try:
        url = urlsplit(value)
        return (
            url.scheme in {"http", "https"}
            and bool(url.hostname)
            and url.username is None
            and url.password is None
            and not url.query
            and not url.fragment
            and (url.port is None or 0 < url.port <= 65535)
        )
    except ValueError:
        return False


def _port(value: str) -> bool:
    return value.isascii() and value.isdecimal() and len(value) <= 5 and 0 < int(value) <= 65535


def _storage(value: str, *, directory: bool) -> bool:
    if "${" in value:
        return False
    path = Path(value)
    if not path.is_absolute():
        return False
    path = path.resolve()
    if workstation.is_installed() and path.is_relative_to(Path(os.path.dirname(os.sys.executable))):
        return False
    if not path.exists():
        return all(parent.is_dir() for parent in path.parents if parent.exists())
    return path.is_dir() if directory else path.is_file()


def _collect(
    compose: dict, app: dict, data: Path, profile: Path
) -> tuple[dict[str, str], dict[str, str]]:
    model = _prompt(
        "Provider/model (for example openai/gpt-4o-mini)",
        compose.get("PRODUCT_PROVIDER_MODEL") or "",
        lambda value: bool(re.fullmatch(r"[^\s/]+/\S+", value)),
    )
    current_key = compose.get("PRODUCT_PROVIDER_API_KEY") or ""
    if current_key == "replace-with-provider-key":
        current_key = ""
    key = _prompt(
        "Provider credential (blank keeps existing)" if current_key else "Provider credential",
        current_key,
        lambda value: bool(value.strip()),
        secret=True,
    )
    endpoint = _prompt(
        "Custom provider API base (optional)",
        compose.get("PRODUCT_PROVIDER_API_BASE") or "",
        _valid_url,
    )
    backend_port = _prompt(
        "Memory backend port", compose.get("WORKSTATION_HINDSIGHT_PORT") or "8888", _port
    )
    proxy_port = _prompt(
        "LLM proxy port",
        compose.get("WORKSTATION_PROXY_PORT") or "4000",
        lambda value: _port(value) and int(value) != int(backend_port),
    )
    archive = _prompt(
        "Archive directory",
        app.get("ENGINEERING_MEMORY_ARCHIVE_ROOT") or str(data / "archive"),
        lambda value: (
            _storage(value, directory=True)
            and not Path(value).resolve().is_relative_to(profile.resolve())
        ),
    )
    state = _prompt(
        "SQLite path",
        app.get("ENGINEERING_MEMORY_IMPORT_STATE_PATH") or str(data / "import-state.db"),
        lambda value: (
            _storage(value, directory=False)
            and not Path(archive).resolve().is_relative_to(Path(value).resolve())
            and not Path(value).resolve().is_relative_to(profile.resolve())
        ),
    )
    proxy_key = compose.get("WORKSTATION_PROXY_KEY") or app.get("ENGINEERING_MEMORY_LLM__API_KEY")
    if not proxy_key or proxy_key == "replace-with-local-proxy-key":
        proxy_key = "sk-" + secrets.token_urlsafe(32)
    return (
        {
            "WORKSTATION_HINDSIGHT_PORT": str(int(backend_port)),
            "WORKSTATION_PROXY_PORT": str(int(proxy_port)),
            "WORKSTATION_PROXY_KEY": proxy_key,
            "PRODUCT_PROVIDER_MODEL": model,
            "PRODUCT_PROVIDER_API_KEY": key,
            "PRODUCT_PROVIDER_API_BASE": endpoint,
        },
        {
            "ENGINEERING_MEMORY_HINDSIGHT__BASE_URL": f"http://127.0.0.1:{int(backend_port)}",
            "ENGINEERING_MEMORY_LLM__BASE_URL": f"http://127.0.0.1:{int(proxy_port)}/v1",
            "ENGINEERING_MEMORY_LLM__API_KEY": proxy_key,
            "ENGINEERING_MEMORY_ARCHIVE_ROOT": Path(archive).resolve().as_posix(),
            "ENGINEERING_MEMORY_IMPORT_STATE_PATH": Path(state).resolve().as_posix(),
        },
    )


def configure(profile: Path, data: Path) -> bool:
    """Recover an interrupted write and offer a coordinated profile update."""
    compose, app = files = (profile / "compose.env", profile / "app.env")
    journal = profile / ".setup-recovery"
    try:
        profile.mkdir(mode=0o700, parents=True, exist_ok=True)
        _private(profile, directory=True)
        with acquisition_lock(profile / ".setup") as acquired:
            if not acquired:
                raise ProfileError("Another setup is editing this profile. Retry when it finishes.")
            for path in (*files, journal):
                if path.is_symlink() or path.is_junction():
                    raise ProfileError("The private profile contains a redirected file.")
                if path.exists():
                    if not path.is_file():
                        raise ProfileError("A private profile entry is not a regular file.")
                    _private(path)
            if journal.exists():
                _restore(journal, files)
            old = tuple(
                path.read_bytes().decode("utf-8") if path.exists() else None for path in files
            )
            compose_values = _compose_values(compose)
            values = _collect(
                compose_values,
                workstation_dotenv(app),
                data,
                profile,
            )
            if not typer.confirm("Save these workstation settings?", default=True):
                return False
            provider_key = "PRODUCT_PROVIDER_API_KEY"
            if values[0][provider_key] == compose_values.get(provider_key):
                # Retain the existing assignment, including any Compose interpolation.
                del values[0][provider_key]
            _atomic_write(journal, json.dumps(old))
            try:
                for path, original, updates in zip(files, old, values, strict=True):
                    _atomic_write(
                        path, _replace_settings(original, updates, compose=path == compose)
                    )
            except (OSError, KeyboardInterrupt):
                _restore(journal, files)
                raise
            journal.unlink()
            _sync_directory(profile)
    except ProfileError:
        raise
    except (OSError, ValueError, AcquisitionError) as error:
        raise ProfileError(
            "Could not update the private profile. Check access and retry."
        ) from error
    return True
