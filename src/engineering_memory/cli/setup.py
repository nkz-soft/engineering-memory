"""Interactive first-run setup for the installed workstation bundle."""

import ctypes
import hashlib
import json
import os
import sys
from contextlib import redirect_stderr, redirect_stdout, suppress
from pathlib import Path

import httpx
import typer

from engineering_memory import cli, setup_clients, setup_history, setup_profile, workstation
from engineering_memory.cli.stack import StackError, check_docker, run_stack
from engineering_memory.settings import (
    WORKSTATION_HTTP_PROXIES,
    SettingsError,
    take_installer_setup_environment,
    workstation_compose_values,
    workstation_setup_overrides,
)


def has_terminal() -> bool:
    return sys.stdin.isatty() and typer.get_text_stream("stdout").isatty()


def _valid_completion(response: httpx.Response) -> bool:
    body = bytearray()
    for chunk in response.iter_bytes(chunk_size=4096):
        if len(body) + len(chunk) > 64 * 1024:
            return False
        body.extend(chunk)
    payload = json.loads(body)
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return False
    message = choices[0].get("message")
    return isinstance(message, dict) and isinstance(message.get("content"), str)


def _check_provider_route(profile: Path) -> None:
    try:
        settings = workstation_compose_values(profile / "compose.env")
    except (OSError, UnicodeError):
        raise StackError("Could not read the private Compose profile. Rerun setup.") from None
    if not any(settings.get(name) for name in WORKSTATION_HTTP_PROXIES):
        return
    if not typer.confirm(
        "Send one synthetic completion to check the provider route?", default=False
    ):
        return

    port = settings.get("WORKSTATION_PROXY_PORT") or "4000"
    key = settings.get("WORKSTATION_PROXY_KEY") or ""
    if not (port.isascii() and port.isdecimal() and len(port) <= 5 and 0 < int(port) <= 65535):
        raise StackError("Check the local LiteLLM port in workstation setup.")
    message = (
        "Provider route check failed. Check the outbound proxy address from the container, "
        "proxy credentials and access policy, and the provider settings. Rerun setup to retry."
    )
    try:
        with (
            httpx.Client(trust_env=False, timeout=httpx.Timeout(30, connect=5)) as client,
            client.stream(
                "POST",
                f"http://127.0.0.1:{int(port)}/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Accept-Encoding": "identity"},
                json={
                    "model": "engineering-extraction",
                    "messages": [{"role": "user", "content": "Reply with OK."}],
                },
            ) as response,
        ):
            if not response.is_success or not _valid_completion(response):
                raise StackError(message)
    except (httpx.HTTPError, ValueError):
        raise StackError(message) from None
    typer.echo("The provider accepted the synthetic completion request.")


def _prepare_backend(profile: Path) -> bool:
    run_stack("check")
    if not typer.confirm("Start the local backend and provision the shared bank?", default=True):
        return False
    run_stack("start")
    _check_provider_route(profile)
    try:
        cli.run_provision({})
    except Exception:
        raise StackError(
            "Bank provisioning failed. Check the backend and provider settings, then retry."
        ) from None
    typer.echo("Shared memory bank provisioned.")
    return True


_INSTALLER_PROTOCOL = "EM1"
_MCP_PROTOCOL = "EM-MCP1"


def _supported_installer_user() -> bool:
    return (
        sys.platform == "win32"
        and workstation.is_installed()
        and not ctypes.windll.shell32.IsUserAnAdmin()
    )


def _installer_save(profile: Path, data: Path, request: dict[str, str]) -> str:
    if request.pop("version", None) != _INSTALLER_PROTOCOL:
        return "request"
    token = request.pop("token", "")
    names = {*setup_profile.INSTALLER_FIELDS, "api_key"}
    if (
        len(token) != 64
        or request.keys() != names
        or any(not value.startswith("v") or len(value) > 8193 for value in request.values())
    ):
        return "request"
    key = request.pop("api_key")[1:]
    fields = {name: value[1:] for name, value in request.items()}
    setup_profile.apply_installer_profile(profile, data, fields, token, key)
    return "saved"


def _installer_start() -> str:
    try:
        run_stack("check")
    except (StackError, SettingsError):
        return "prerequisite"
    try:
        run_stack("start")
    except (StackError, SettingsError):
        return "startup"
    try:
        cli.run_provision({})
    except Exception:
        return "bank"
    return "ready"


def _encoded(value: str) -> str:
    return "v" + value.encode().hex()


def _mcp_scan(executable: Path):
    clients = setup_clients.discover()
    reviews = []
    for target in setup_clients.group_targets(clients):
        review = setup_clients.inspect(target, executable)
        ids = ",".join(sorted(client.id for client in target.clients))
        token = (
            hashlib.sha256(f"{review.token}:{ids}".encode()).hexdigest() if review.token else "-"
        )
        reviews.append((token, review))
    return clients, reviews


def _installer_mcp(action: str, request: dict[str, str]) -> tuple[str, ...]:
    executable = Path(sys.executable).absolute()
    if action == "mcp-scan" and not request:
        clients, reviews = _mcp_scan(executable)
        output = [_MCP_PROTOCOL]
        for token, review in reviews:
            output.extend(
                (
                    token,
                    review.state,
                    _encoded(", ".join(client.name for client in review.target.clients)),
                    _encoded(str(review.target.config)),
                    _encoded(review.diagnostic),
                )
            )
        for client in clients:
            if client.config is None:
                output.extend(
                    (
                        "-",
                        "blocked",
                        _encoded(client.name),
                        "v",
                        _encoded(client.diagnostic or setup_clients.PROFILE_RESOLUTION),
                    )
                )
        return tuple(output)
    if action == "mcp-apply" and request.keys() == {"mcp"}:
        consent = request["mcp"]
        if len(consent) > 72:
            return ("request",)
        token, _, decision = consent.partition(":")
        if len(token) != 64 or decision not in {"keep", "replace"}:
            return ("request",)
        _, reviews = _mcp_scan(executable)
        for current, review in reviews:
            if current == token:
                result = setup_clients.verify(review, executable, replace=decision == "replace")
                return _MCP_PROTOCOL, result.state, result.probe, _encoded(result.diagnostic)
        return (
            _MCP_PROTOCOL,
            "blocked",
            "skipped",
            _encoded("The target or its configuration changed. Go back to rescan and retry."),
        )
    return ("request",)


def _installer_output(action: str, request: dict[str, str]) -> tuple[str, ...]:
    if not _supported_installer_user():
        return ("user",)
    if action in {"mcp-scan", "mcp-apply"}:
        return _installer_mcp(action, request)
    if workstation_setup_overrides():
        return ("overrides",)
    profile, data = workstation.locations()
    if action == "read":
        fields, has_key, token = setup_profile.read_installer_profile(profile, data)
        # ASCII framing preserves empty fields and UTF-8 through Inno's pipe reader.
        encoded = tuple(
            "v" + fields[name].encode().hex() for name in setup_profile.INSTALLER_FIELDS
        )
        return (_INSTALLER_PROTOCOL, str(int(has_key)), token, *encoded)
    if action == "save":
        return (_installer_save(profile, data, request),)
    if action == "start":
        return (_installer_start(),)
    return ("request",)


def _run_installer_ui(action: str) -> None:
    request = take_installer_setup_environment()
    try:
        with (
            open(os.devnull, "w", encoding="utf-8") as quiet,
            redirect_stdout(quiet),
            redirect_stderr(quiet),
        ):
            output = _installer_output(action, request)
    except setup_profile.InstallerProfileError as error:
        output = (str(error),)
    except Exception:
        output = ("profile",)
    typer.echo("\n".join(output))
    if output[0] not in {_INSTALLER_PROTOCOL, _MCP_PROTOCOL, "saved", "ready"}:
        raise typer.Exit(1)


def setup_command(
    installer: bool = typer.Option(False, "--installer", hidden=True),
    installer_ui: str | None = typer.Option(None, "--installer-ui", hidden=True),
) -> None:
    """Configure the workstation profile, backend, coding agents and optional history."""
    if installer_ui is not None:
        _run_installer_ui(installer_ui)
        return
    try:
        _run_setup()
    finally:
        if installer and has_terminal():
            with suppress(EOFError, KeyboardInterrupt):
                input("Press Enter to close setup.")


def _run_setup() -> None:
    if not has_terminal():
        typer.echo("Run engineering-memory setup in an interactive terminal.", err=True)
        raise typer.Exit(1)
    if not workstation.is_installed():
        typer.echo("Run setup with the installed workstation executable.", err=True)
        raise typer.Exit(1)
    if os.name != "nt" and os.geteuid() == 0:
        typer.echo("Run setup from your own user session without sudo.", err=True)
        raise typer.Exit(1)

    overrides = workstation_setup_overrides()
    if overrides:
        typer.echo(
            "Unset these environment overrides in this terminal before running setup: "
            + ", ".join(overrides),
            err=True,
        )
        raise typer.Exit(1)

    stages = []
    backend_ready = False
    profile_failed = False
    try:
        check_docker()
        profile, data = workstation.locations()
        if setup_profile.configure(profile, data):
            stages.append("Profile saved")
            backend_ready = _prepare_backend(profile)
        if backend_ready:
            stages.append("Backend ready and bank provisioned")
        else:
            stages.append("Backend and history import deferred")
    except (setup_profile.ProfileError, StackError) as error:
        typer.echo(str(error), err=True)
        stages.append("History import deferred. Rerun setup to retry")
        profile_failed = True
    except (typer.Abort, KeyboardInterrupt, EOFError):
        typer.echo(". ".join([*stages, "Setup deferred. Rerun setup to continue."]))
        return

    try:
        clients = setup_clients.configure(Path(sys.executable).absolute())
        stages.append(
            "MCP registration reviewed" if clients else "MCP registration needs attention"
        )
        history = True
        if backend_ready:
            history = setup_history.import_selected()
            stages.append(
                "History selection reviewed" if history else "History import needs attention"
            )
    except (typer.Abort, KeyboardInterrupt, EOFError):
        typer.echo(". ".join([*stages, "Remaining setup deferred. Rerun setup to continue."]))
        return

    typer.echo(". ".join(stages) + ".")
    if profile_failed or not (clients and history):
        raise typer.Exit(1)
