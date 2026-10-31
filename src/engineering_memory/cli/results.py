"""Stable safe presentation; no exception text belongs in command results."""

import json

import typer


def result(command: str) -> dict:
    data = {"schema_version": 1, "command": command, "status": "success", "error": None}
    if command == "provision":
        data.update(bank=None, mission_verified=False)
    elif command == "import":
        data.update(imported=0, skipped=0, failed=0, terminal_error=None, outcomes=[])
    else:
        data.update(imported=0, failed=0, records=[])
    return data


def emit(data: dict, *, structured: bool) -> None:
    if structured:
        typer.echo(json.dumps(data, ensure_ascii=True))
        return
    if data["error"]:
        messages = {"configuration": "configuration invalid", "memory": "memory unavailable"}
        typer.echo(messages.get(data["error"], f"{data['error']}: command failed"), err=True)
    if data["command"] == "provision":
        if data["mission_verified"]:
            typer.echo("Bank retain mission verified.")
    elif data["command"] == "import":
        typer.echo(
            f"Imported: {data['imported']}; skipped: {data['skipped']}; failed: {data['failed']}"
        )
        for row in data["outcomes"]:
            if row["error"]:
                typer.echo(f"{row['source_id'] or '<unknown>'}: {row['error']}")
        if data["terminal_error"]:
            typer.echo(f"Terminal error: {data['terminal_error']}")
    else:
        typer.echo(f"Latest state: imported: {data['imported']}; failed: {data['failed']}")
        for row in data["records"]:
            typer.echo(f"{row['source']}:{row['source_id']}: {row['status']} {row['error'] or ''}")
        typer.echo("Skips are per-run outcomes and are not stored in latest state.")
