"""Operator CLI; feature 016 adds explicit bank provisioning before import."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import typer

app = typer.Typer(
    name="engineering-memory",
    help="Engineering memory: private conversation history, retained and recallable.",
    no_args_is_help=True,
    add_completion=False,
)


def _version() -> str:
    """The installed distribution's version, or a marker when running from an unbuilt tree."""
    try:
        return version("engineering-memory")
    except PackageNotFoundError:  # pragma: no cover - only outside an installed environment
        return "unknown"


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"engineering-memory {_version()}")
        raise typer.Exit


@app.callback()
def main_callback(
    _version_flag: bool = typer.Option(
        False,
        "--version",
        callback=_print_version,
        is_eager=True,
        help="Show the installed version and exit.",
    ),
) -> None:
    """Engineering memory: private conversation history, retained and recallable."""


def main() -> None:
    """The console-script entry point declared in `pyproject.toml`."""
    app()


@app.command("provision")
def provision_command() -> None:
    """Prepare the shared bank and verify its retain mission before import."""
    from engineering_memory.memory.hindsight.provision import ProvisionError, provision
    from engineering_memory.settings import SettingsError, load_settings

    try:
        provision(load_settings().hindsight)
    except (SettingsError, ProvisionError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None
    typer.echo("Bank retain mission verified.")
