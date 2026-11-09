"""Stable safe presentation; no exception text belongs in command results."""

import json

import typer


def result(command: str, *, dry_run: bool = False) -> dict:
    data = {"schema_version": 1, "command": command, "status": "success", "error": None}
    if command == "provision":
        data.update(bank=None, mission_verified=False)
    elif command == "models refresh":
        data.update(project=None, models=[])
    elif command == "import":
        if dry_run:
            data.update(
                dry_run=True,
                would_import=0,
                would_skip=0,
                failed=0,
                terminal_error=None,
                outcomes=[],
            )
        else:
            data.update(imported=0, skipped=0, failed=0, terminal_error=None, outcomes=[])
    elif command == "acquire-chatgpt":
        data.update(
            outcome="empty", digest=None, imported=0, skipped=0, failed=0, terminal_error=None
        )
    else:
        data.update(imported=0, failed=0, records=[], last_chatgpt_export=None)
    return data


def emit(data: dict, *, structured: bool) -> None:
    if structured:
        typer.echo(json.dumps(data, ensure_ascii=True))
        return
    if data["error"]:
        messages = {"configuration": "configuration invalid", "memory": "memory unavailable"}
        typer.echo(messages.get(data["error"], f"{data['error']}: command failed"), err=True)
    if data["command"] == "models refresh":
        for row in data["models"]:
            typer.echo(f"{row['kind']}: {row['status']} {row['error'] or ''}".rstrip())
    elif data["command"] == "provision":
        if data["mission_verified"]:
            typer.echo("Bank retain mission verified.")
    elif data.get("dry_run"):
        typer.echo(
            f"Dry run: would import: {data['would_import']}; "
            f"would skip: {data['would_skip']}; failed: {data['failed']}"
        )
        for row in data["outcomes"]:
            typer.echo(
                f"{row['document_id'] or '<unknown>'} {row['project'] or '-'} "
                f"{row['timestamp'] or '-'} "
                f"redactions={','.join(row['redaction_categories']) or 'none'} "
                f"{row['decision']} {row['error'] or ''}"
            )
        if data["terminal_error"]:
            typer.echo(f"Terminal error: {data['terminal_error']}")
    elif data["command"] == "import":
        typer.echo(
            f"Imported: {data['imported']}; skipped: {data['skipped']}; failed: {data['failed']}"
        )
        for row in data["outcomes"]:
            if row["error"]:
                typer.echo(f"{row['source_id'] or '<unknown>'}: {row['error']}")
        if data["terminal_error"]:
            typer.echo(f"Terminal error: {data['terminal_error']}")
    elif data["command"] == "acquire-chatgpt":
        typer.echo(
            f"Export acquisition: {data['outcome']}. "
            f"Imported: {data['imported']}; skipped: {data['skipped']}; failed: {data['failed']}"
        )
        if data["digest"]:
            typer.echo(f"Archive digest: {data['digest']}")
        if data["terminal_error"]:
            typer.echo(f"Terminal error: {data['terminal_error']}")
    else:
        typer.echo(f"Latest state: imported: {data['imported']}; failed: {data['failed']}")
        if export := data["last_chatgpt_export"]:
            produced = export["produced_at"] or "unknown"
            typer.echo(
                f"Last ChatGPT export produced: {produced} ({export['production_evidence']})"
            )
            typer.echo(f"Last ChatGPT export imported: {export['ingested_at']}")
        else:
            typer.echo("Last ChatGPT export: no completed acquisition.")
        for row in data["records"]:
            typer.echo(f"{row['source']}:{row['source_id']}: {row['status']} {row['error'] or ''}")
        typer.echo("Skips are per-run outcomes and are not stored in latest state.")
