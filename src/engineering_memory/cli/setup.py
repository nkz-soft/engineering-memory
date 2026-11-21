"""Interactive first-run setup for the installed workstation bundle."""

import json
import os
import sys
from contextlib import suppress
from pathlib import Path

import httpx
import typer

from engineering_memory import cli, setup_clients, setup_history, setup_profile, workstation
from engineering_memory.cli.stack import StackError, check_docker, run_stack
from engineering_memory.settings import (
    WORKSTATION_HTTP_PROXIES,
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


def setup_command(
    installer: bool = typer.Option(False, "--installer", hidden=True),
) -> None:
    """Configure the workstation profile, backend, coding agents and optional history."""
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
        check_docker()
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
