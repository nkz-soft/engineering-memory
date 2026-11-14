"""Interactive first-run setup for the installed workstation bundle."""

import os
import sys
from contextlib import suppress
from pathlib import Path

import typer

from engineering_memory import cli, setup_clients, setup_history, setup_profile, workstation
from engineering_memory.cli.stack import StackError, run_stack
from engineering_memory.settings import workstation_setup_overrides


def has_terminal() -> bool:
    return sys.stdin.isatty() and typer.get_text_stream("stdout").isatty()


def _prepare_backend() -> None:
    run_stack("check")
    if not typer.confirm("Start the local backend and provision the shared bank?", default=True):
        raise typer.Abort
    run_stack("start")
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
        if not setup_profile.configure(*workstation.locations()):
            raise typer.Abort
        stages.append("Profile saved")
        _prepare_backend()
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
