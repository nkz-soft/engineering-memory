"""Operator commands for explicit provisioning, ingestion and offline state inspection."""

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


def _execute(command, structured, action):
    from engineering_memory.cli.results import emit, result
    from engineering_memory.cli.runtime import error_category

    data = result(command)
    code = 0
    try:
        action(data)
        if data["status"] != "success":
            code = 1
    except KeyboardInterrupt:
        data.update(status="failure", error="interrupted")
        code = 130
    except Exception as error:
        data.update(status="failure", error=error_category(error))
        code = 1
    emit(data, structured=structured)
    raise typer.Exit(code)


@app.command("provision")
def provision_command(
    structured: bool = typer.Option(False, "--json", help="Emit one JSON result."),
) -> None:
    """Prepare the shared bank and verify its retain mission before import."""

    def run(data):
        from engineering_memory.memory.hindsight.provision import provision
        from engineering_memory.settings import load_settings

        settings = load_settings()
        data["bank"] = settings.hindsight.bank_id
        provision(settings.hindsight)
        data["mission_verified"] = True

    _execute("provision", structured, run)


@app.command("import")
def import_command(
    export: str | None = typer.Option(
        None, "--export", help="ChatGPT ZIP, export directory or conversations JSON."
    ),
    from_archive: bool = typer.Option(False, "--from-archive", help="Replay archived originals."),
    force: bool = typer.Option(False, "--force", help="Reprocess unchanged conversations."),
    structured: bool = typer.Option(False, "--json", help="Emit one JSON result."),
) -> None:
    """Import ChatGPT history from exactly one source."""
    from engineering_memory.cli.results import emit, result
    from engineering_memory.cli.runtime import run_import

    if (export is None) == (not from_archive):
        data = result("import")
        data.update(status="failure", error="usage")
        emit(data, structured=structured)
        raise typer.Exit(2)
    _execute("import", structured, lambda data: run_import(data, export, force, _version()))


@app.command("status")
def status_command(
    structured: bool = typer.Option(False, "--json", help="Emit one JSON result."),
) -> None:
    """Inspect latest import state offline without modifying storage."""
    from engineering_memory.cli.runtime import run_status

    _execute("status", structured, run_status)
