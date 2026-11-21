"""Collect and persist the private workstation profile."""

import json
import os
import re
import secrets
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from io import StringIO
from ipaddress import IPv6Address
from pathlib import Path
from urllib.parse import urlsplit

import typer

from engineering_memory import workstation
from engineering_memory.ingestion.acquisition_lock import acquisition_lock
from engineering_memory.ingestion.acquisition_source import AcquisitionError
from engineering_memory.settings import (
    WORKSTATION_HTTP_PROXIES,
    WORKSTATION_NO_PROXY,
    workstation_compose_values,
    workstation_dotenv,
    workstation_dotenv_entries,
)


class ProfileError(RuntimeError):
    """A safe message about profile configuration."""


class InstallerProfileError(ProfileError):
    """A fixed installer status identifying an invalid field or stale profile."""


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
        if _plain(value) and valid(value):
            return value
        typer.echo(f"Invalid {label.lower()}. Enter a valid value.", err=True)


def _plain(value: str) -> bool:
    return all(ord(char) >= 32 and ord(char) != 127 for char in value)


def _valid_model(value: str) -> bool:
    return bool(re.fullmatch(r"[^\s/]+/\S+", value))


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


def _valid_proxy_url(value: str) -> bool:
    if not value or any(char.isspace() or char == "\\" for char in value):
        return False
    if any(char in value for char in "?#") or re.search(r"%(?![0-9a-fA-F]{2})", value):
        return False
    try:
        url = urlsplit(value)
        return (
            url.scheme in {"http", "https"}
            and bool(url.hostname)
            and url.netloc.count("@") <= 1
            and url.path in {"", "/"}
            and (url.port is None or 0 < url.port <= 65535)
        )
    except ValueError:
        return False


def _proxy_url(scheme: str, current: str) -> str:
    state = "configured" if current else "unset"
    action = _prompt(
        f"Outbound proxy for {scheme} destinations ({state}, keep/set/clear)",
        "keep",
        {"keep", "set", "clear"}.__contains__,
    )
    if action == "set":
        return _prompt(f"{scheme} destination proxy URL", "", _valid_proxy_url, secret=True)
    return current if action == "keep" else ""


def _valid_bypass_host(host: str) -> bool:
    host = host.strip()
    if ":" in host:
        try:
            IPv6Address(host)
        except ValueError:
            return False
        return "%" not in host
    return (
        re.fullmatch(
            r"\.?[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?"
            r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.?",
            host,
        )
        is not None
    )


def _valid_bypass(value: str) -> bool:
    return value in {"", "-"} or all(_valid_bypass_host(host) for host in value.split(","))


def _port(value: str) -> bool:
    return value.isascii() and value.isdecimal() and len(value) <= 5 and 0 < int(value) <= 65535


def _storage(value: str, *, directory: bool) -> bool:
    if "${" in value or (os.name == "nt" and os.path.isreserved(value)):
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


def _archive_location(value: str, profile: Path) -> bool:
    return _storage(value, directory=True) and not Path(value).resolve().is_relative_to(
        profile.resolve()
    )


def _sqlite_location(value: str, archive: str, profile: Path) -> bool:
    return (
        _storage(value, directory=False)
        and not Path(archive).resolve().is_relative_to(Path(value).resolve())
        and not Path(value).resolve().is_relative_to(profile.resolve())
    )


def _provider_key(compose: dict[str, str]) -> str:
    key = compose.get("PRODUCT_PROVIDER_API_KEY") or ""
    return "" if key == "replace-with-provider-key" else key


def _collect(
    compose: dict, app: dict, data: Path, profile: Path
) -> tuple[dict[str, str], dict[str, str]]:
    model = _prompt(
        "Provider/model (for example openai/gpt-4o-mini)",
        compose.get("PRODUCT_PROVIDER_MODEL") or "",
        _valid_model,
    )
    current_key = _provider_key(compose)
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
        lambda value: _archive_location(value, profile),
    )
    state = _prompt(
        "SQLite path",
        app.get("ENGINEERING_MEMORY_IMPORT_STATE_PATH") or str(data / "import-state.db"),
        lambda value: _sqlite_location(value, archive, profile),
    )
    network_proxies = {
        name: _proxy_url(scheme, compose.get(name) or "")
        for name, scheme in zip(WORKSTATION_HTTP_PROXIES, ("HTTP", "HTTPS"), strict=True)
    }
    bypass = _prompt(
        "Additional outbound proxy bypass hosts (comma separated, '-' clears)",
        compose.get(WORKSTATION_NO_PROXY) or "",
        _valid_bypass,
    )
    network_proxies[WORKSTATION_NO_PROXY] = (
        "" if bypass in {"", "-"} else ",".join(host.strip() for host in bypass.split(","))
    )
    fields = {
        "model": model,
        "api_base": endpoint,
        "backend_port": backend_port,
        "litellm_port": proxy_port,
        "archive": archive,
        "sqlite": state,
    }
    compose_updates, app_updates = _settings_updates(compose, app, fields, key)
    compose_updates.update(network_proxies)
    return compose_updates, app_updates


def _settings_updates(
    compose: dict[str, str], app: dict[str, str], fields: dict[str, str], key: str
) -> tuple[dict[str, str], dict[str, str]]:
    backend_port = int(fields["backend_port"])
    proxy_port = int(fields["litellm_port"])
    proxy_key = compose.get("WORKSTATION_PROXY_KEY") or app.get("ENGINEERING_MEMORY_LLM__API_KEY")
    if not proxy_key or proxy_key == "replace-with-local-proxy-key":
        proxy_key = "sk-" + secrets.token_urlsafe(32)
    return (
        {
            "WORKSTATION_HINDSIGHT_PORT": str(backend_port),
            "WORKSTATION_PROXY_PORT": str(proxy_port),
            "WORKSTATION_PROXY_KEY": proxy_key,
            "PRODUCT_PROVIDER_MODEL": fields["model"],
            "PRODUCT_PROVIDER_API_KEY": key,
            "PRODUCT_PROVIDER_API_BASE": fields["api_base"],
        },
        {
            "ENGINEERING_MEMORY_HINDSIGHT__BASE_URL": f"http://127.0.0.1:{backend_port}",
            "ENGINEERING_MEMORY_LLM__BASE_URL": f"http://127.0.0.1:{proxy_port}/v1",
            "ENGINEERING_MEMORY_LLM__API_KEY": proxy_key,
            "ENGINEERING_MEMORY_ARCHIVE_ROOT": Path(fields["archive"]).resolve().as_posix(),
            "ENGINEERING_MEMORY_IMPORT_STATE_PATH": Path(fields["sqlite"]).resolve().as_posix(),
        },
    )


def _readable(path: Path) -> bool:
    if path.is_symlink() or path.is_junction():
        raise ProfileError("The private profile contains a redirected path. Check its location.")
    return path.exists()


@contextmanager
def _locked_profile(profile: Path, *, create: bool) -> Iterator[None]:
    try:
        if create:
            profile.mkdir(mode=0o700, parents=True, exist_ok=True)
        _private(profile, directory=True)
        with acquisition_lock(profile / ".setup") as acquired:
            if not acquired:
                raise ProfileError("Another setup is editing this profile. Retry when it finishes.")
            compose, app = _profile_files(profile)
            journal = profile / ".setup-recovery"
            for path in (compose, app, journal):
                if _readable(path):
                    if not path.is_file():
                        raise ProfileError("A private profile entry is not a regular file.")
                    _private(path)
            if journal.exists():
                _restore(journal, (compose, app))
            yield
    except (OSError, ValueError, AcquisitionError):
        raise ProfileError(
            "Could not update the private profile. Check access and retry."
        ) from None


def _profile_files(profile: Path) -> tuple[Path, Path]:
    return profile / "compose.env", profile / "app.env"


def _persist(
    profile: Path, compose: dict[str, str], values: tuple[dict[str, str], dict[str, str]]
) -> None:
    files = _profile_files(profile)
    journal = profile / ".setup-recovery"
    old = tuple(path.read_bytes().decode("utf-8") if path.exists() else None for path in files)
    provider_key = "PRODUCT_PROVIDER_API_KEY"
    if values[0][provider_key] == compose.get(provider_key):
        # Retain the existing assignment, including any Compose interpolation.
        del values[0][provider_key]
    _atomic_write(journal, json.dumps(old))
    try:
        for index, (path, original, updates) in enumerate(zip(files, old, values, strict=True)):
            _atomic_write(path, _replace_settings(original, updates, compose=index == 0))
    except (OSError, KeyboardInterrupt):
        _restore(journal, files)
        raise
    journal.unlink()
    _sync_directory(profile)


def configure(profile: Path, data: Path) -> bool:
    """Recover an interrupted write and offer a coordinated profile update."""
    with _locked_profile(profile, create=True):
        compose_file, app_file = _profile_files(profile)
        compose = workstation_compose_values(compose_file)
        values = _collect(compose, workstation_dotenv(app_file), data, profile)
        if not typer.confirm("Save these workstation settings?", default=True):
            return False
        _persist(profile, compose, values)
    return True


INSTALLER_FIELDS = (
    "provider",
    "model",
    "api_base",
    "backend_port",
    "litellm_port",
    "archive",
    "sqlite",
)


def _installer_snapshot(
    compose: dict[str, str], app: dict[str, str], data: Path
) -> tuple[dict[str, str], bool, str]:
    model_id = compose.get("PRODUCT_PROVIDER_MODEL") or ""
    endpoint = compose.get("PRODUCT_PROVIDER_API_BASE") or ""
    if not model_id and not compose and not app:
        model_id = "openrouter/openai/gpt-oss-20b"
        endpoint = "https://openrouter.ai/api/v1"
    provider, separator, model = model_id.partition("/")
    fields = {
        "provider": provider if separator else "",
        "model": model if separator else provider,
        "api_base": endpoint if _plain(endpoint) and _valid_url(endpoint) else "",
        "backend_port": compose.get("WORKSTATION_HINDSIGHT_PORT") or "8888",
        "litellm_port": compose.get("WORKSTATION_PROXY_PORT") or "4000",
        "archive": app.get("ENGINEERING_MEMORY_ARCHIVE_ROOT") or str(data / "archive"),
        "sqlite": app.get("ENGINEERING_MEMORY_IMPORT_STATE_PATH") or str(data / "import-state.db"),
    }
    has_key = bool(_provider_key(compose).strip())
    token = sha256(json.dumps([fields, has_key], sort_keys=True).encode()).hexdigest()
    return fields, has_key, token


def read_installer_profile(profile: Path, data: Path) -> tuple[dict[str, str], bool, str]:
    """Read only the fields the wizard edits, without exposing the saved credential."""
    if not _readable(profile):
        return _installer_snapshot({}, {}, data)
    with _locked_profile(profile, create=False):
        compose, app = _profile_files(profile)
        return _installer_snapshot(
            workstation_compose_values(compose), workstation_dotenv(app), data
        )


def _check_installer_fields(fields: dict[str, str], profile: Path, key: str) -> None:
    if fields.keys() != set(INSTALLER_FIELDS):
        raise InstallerProfileError("request")
    for field, value in fields.items():
        if not _plain(value):
            raise InstallerProfileError(field)
    if not re.fullmatch(r"[^\s/]+", fields["provider"]):
        raise InstallerProfileError("provider")
    if not _valid_model(fields["provider"] + "/" + fields["model"]):
        raise InstallerProfileError("model")
    if not _valid_url(fields["api_base"]) or any(c.isspace() for c in fields["api_base"]):
        raise InstallerProfileError("api_base")
    if not _port(fields["backend_port"]):
        raise InstallerProfileError("backend_port")
    if not _port(fields["litellm_port"]) or int(fields["backend_port"]) == int(
        fields["litellm_port"]
    ):
        raise InstallerProfileError("litellm_port")
    if not _archive_location(fields["archive"], profile):
        raise InstallerProfileError("archive")
    if not _sqlite_location(fields["sqlite"], fields["archive"], profile):
        raise InstallerProfileError("sqlite")
    if key and (not _plain(key) or not key.strip()):
        raise InstallerProfileError("api_key")


def apply_installer_profile(
    profile: Path, data: Path, fields: dict[str, str], token: str, key: str
) -> None:
    """Apply an approved wizard edit while preserving the newest hidden settings."""
    try:
        _check_installer_fields(fields, profile, key)
    except (OSError, ValueError):
        raise InstallerProfileError("storage") from None
    with _locked_profile(profile, create=True):
        compose_file, app_file = _profile_files(profile)
        compose = workstation_compose_values(compose_file)
        app = workstation_dotenv(app_file)
        current, has_key, current_token = _installer_snapshot(compose, app, data)
        if token != current_token:
            raise InstallerProfileError("stale")
        if not key and (not has_key or fields["provider"] != current["provider"]):
            raise InstallerProfileError("api_key")
        model = fields["provider"] + "/" + fields["model"]
        values = _settings_updates(
            compose, app, {**fields, "model": model}, key or _provider_key(compose)
        )
        for updates, saved, name in (
            (values[0], compose, "WORKSTATION_PROXY_KEY"),
            (values[1], app, "ENGINEERING_MEMORY_LLM__API_KEY"),
        ):
            if updates[name] == saved.get(name):
                del updates[name]
        _persist(profile, compose, values)
