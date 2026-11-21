"""Interactive first-run setup for the installed workstation bundle."""

import ctypes
import json
import os
import sys
from contextlib import redirect_stderr, redirect_stdout, suppress
from pathlib import Path

import httpx
import typer

from engineering_memory import cli, setup_clients, setup_history, setup_profile, workstation
from engineering_memory.cli.stack import StackError, run_stack
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


def _prepare_backend(profile: Path) -> None:
    run_stack("check")
    if not typer.confirm("Start the local backend and provision the shared bank?", default=True):
        raise typer.Abort
    run_stack("start")
    _check_provider_route(profile)
    try:
        cli.run_provision({})
    except Exception:
        raise StackError(
            "Bank provisioning failed. Check the backend and provider settings, then retry."
        ) from None
    typer.echo("Shared memory bank provisioned.")


_INSTALLER_PROTOCOL = "EM1"


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


def _installer_output(action: str, request: dict[str, str]) -> tuple[str, ...]:
    if not _supported_installer_user():
        return ("user",)
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
    if output[0] not in {_INSTALLER_PROTOCOL, "saved", "ready"}:
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
    try:
        profile, data = workstation.locations()
        if not setup_profile.configure(profile, data):
            raise typer.Abort
        stages.append("Profile saved")
        _prepare_backend(profile)
        stages.append("Backend ready and bank provisioned")
    except (setup_profile.ProfileError, StackError) as error:
        typer.echo(str(error), err=True)
        typer.echo(". ".join([*stages, "History import deferred. Rerun setup to retry."]))
        raise typer.Exit(1) from None
    except (typer.Abort, KeyboardInterrupt, EOFError):
        typer.echo(". ".join([*stages, "Setup deferred. Rerun setup to continue."]))
        return

    try:
        clients = setup_clients.configure(Path(sys.executable).absolute())
        stages.append(
            "MCP registration reviewed" if clients else "MCP registration needs attention"
        )
        history = setup_history.import_selected()
        stages.append("History selection reviewed" if history else "History import needs attention")
    except (typer.Abort, KeyboardInterrupt, EOFError):
        typer.echo(". ".join([*stages, "Remaining setup deferred. Rerun setup to continue."]))
        return

    typer.echo(". ".join(stages) + ".")
    if not (clients and history):
        raise typer.Exit(1)
