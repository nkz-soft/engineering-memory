"""Stage, review and approve project procedures on the operator workstation."""

import json
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(help="Manage local reviewed project playbooks.", no_args_is_help=True)

_MAX_FILE_BYTES = 512 * 1024
_ERRORS = {
    "invalid_input": "Check the project, playbook ID, revision and draft format.",
    "example_unavailable": (
        "Check that each example exists in this project, then stage and review again."
    ),
    "draft_changed": "The pending draft changed. Review it and approve its current revision.",
    "draft_not_found": "No pending draft was found. Stage a draft first.",
    "catalog_unavailable": "Check access to the configured local playbook catalog.",
}


def _execute(operation):
    from engineering_memory.cli.runtime import make_playbook_operator
    from engineering_memory.settings import SettingsError

    try:
        return operation(make_playbook_operator())
    except SettingsError:
        typer.echo("Check the local archive configuration.", err=True)
    except ValueError as error:
        typer.echo(_ERRORS.get(str(error), _ERRORS["invalid_input"]), err=True)
    raise typer.Exit(1)


def _draft_file(file: Path):
    try:
        with file.open("rb") as stream:
            raw = stream.read(_MAX_FILE_BYTES + 1)
        if len(raw) <= _MAX_FILE_BYTES:
            return json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, RecursionError):
        pass
    raise ValueError("invalid_input")


@app.command()
def stage(
    project: Annotated[str, typer.Option()],
    id: Annotated[str, typer.Option()],
    file: Annotated[Path, typer.Option()],
) -> None:
    """Validate a local draft file and print its revision."""
    draft = _execute(lambda operator: operator.stage(project, id, _draft_file(file)))
    typer.echo(draft.revision)


@app.command()
def review(project: Annotated[str, typer.Option()], id: Annotated[str, typer.Option()]) -> None:
    """Print a pending revision for review."""
    draft = _execute(lambda operator: operator.review(project, id))
    typer.echo(f"Revision {draft.revision}")
    title = draft.content.title.replace("\n", "\n       ")
    typer.echo(f"Title: {title}")
    for number, step in enumerate(draft.content.steps, 1):
        prefix = f"{number}. "
        continuation = "\n" + " " * len(prefix)
        typer.echo(prefix + step.replace("\n", continuation))
    for example in draft.content.examples:
        typer.echo(
            f"Example {example.document_id} ({example.project}, "
            f"{example.source_timestamp.isoformat()}, snapshot {example.snapshot})"
        )


@app.command()
def approve(
    project: Annotated[str, typer.Option()],
    id: Annotated[str, typer.Option()],
    revision: Annotated[str, typer.Option()],
) -> None:
    """Publish the reviewed revision and print its version."""
    typer.echo(_execute(lambda operator: operator.approve(project, id, revision)))
