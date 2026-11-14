"""Discover selectable local histories and import through the operator paths."""

import os
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import typer

from engineering_memory.cli.runtime import error_category, run_import
from engineering_memory.ingestion.chatgpt.export import Export as ChatGPTExport
from engineering_memory.ingestion.chatgpt.records import RecordScanner
from engineering_memory.ingestion.claude_chat.export import Export as ClaudeExport
from engineering_memory.ingestion.source import SourceFormatError, SourceUnavailable
from engineering_memory.settings import load_settings
from engineering_memory.setup_clients import profile_roots

EXPORTS = {"chatgpt": ChatGPTExport, "claude-chat": ClaudeExport}


@dataclass(frozen=True)
class Candidate:
    source: str
    path: Path


def _safe_path(path: Path) -> bool:
    return not any(part.is_symlink() or part.is_junction() for part in (path, *path.parents))


def _agent_files(root: Path):
    if not _safe_path(root):
        return
    for directory, subdirectories, names in root.walk():
        subdirectories[:] = sorted(name for name in subdirectories if _safe_path(directory / name))
        for name in sorted(names):
            path = directory / name
            if path.suffix.lower() == ".jsonl" and _safe_path(path) and path.is_file():
                yield path


def _safe_members(path: Path, names: tuple[str, ...]) -> bool:
    return not path.is_dir() or all(_safe_path(path / name) for name in names)


def _export_at(source: str, path: Path) -> Candidate | None:
    if not _safe_path(path):
        return None
    try:
        with EXPORTS[source](path) as export:
            if not _safe_members(path, export.names):
                return None
    except (OSError, SourceUnavailable, SourceFormatError):
        return None
    return Candidate(source, path)


def _detect_export(path: Path) -> Candidate | None:
    if not _safe_path(path) or (not path.is_dir() and path.suffix.lower() not in {".json", ".zip"}):
        return None
    try:
        with ChatGPTExport(path) as export:
            if not _safe_members(path, export.names):
                return None
            for name in export.names:
                with export.open(name) as stream:
                    record = next(RecordScanner(stream, max_record_chars=8 * 1024 * 1024), None)
                if record is None:
                    continue
                fields = record.value
                if isinstance(fields, dict):
                    if "mapping" in fields and ("id" in fields or "conversation_id" in fields):
                        return Candidate("chatgpt", path)
                    if "uuid" in fields and "chat_messages" in fields:
                        return _export_at("claude-chat", path)
                return None
    except (OSError, SourceUnavailable, SourceFormatError):
        return None
    return None


def discover(inbox: Path | None) -> list[Candidate]:
    roots = profile_roots()
    candidates = [
        Candidate(source, path)
        for source, root in (
            ("codex", roots["Codex"] / "sessions"),
            ("claude-code", roots["Claude Code"] / "projects"),
        )
        for path in _agent_files(root)
    ]
    if inbox is not None and _safe_path(inbox):
        try:
            entries = sorted(inbox.iterdir())
        except OSError:
            typer.echo("The configured export inbox is unavailable. You can enter another path.")
        else:
            for path in entries:
                if candidate := _detect_export(path):
                    candidates.append(candidate)
    return _unique(candidates)


def _unique(candidates: list[Candidate]) -> list[Candidate]:
    unique = {}
    for entry in candidates:
        key = entry.source, os.path.normcase(str(entry.path.resolve()))
        unique.setdefault(key, entry)
    return list(unique.values())


def _manual_exports() -> list[Candidate]:
    candidates = []
    while typer.confirm("Add a local chat export by path?", default=False):
        source = typer.prompt("Export type (chatgpt or claude-chat)", default="chatgpt")
        if source not in EXPORTS:
            typer.echo("Choose chatgpt or claude-chat.")
            continue
        path = Path(typer.prompt("Export path").strip().strip('"')).expanduser().absolute()
        if candidate := _export_at(source, path):
            candidates.append(candidate)
        else:
            typer.echo("No supported export at that path. Check the path and export type.")
    return candidates


def _import_candidate(candidate: Candidate, installed_version: str) -> bool:
    try:
        if not _safe_path(candidate.path) or (
            candidate.path.is_dir() and _export_at(candidate.source, candidate.path) is None
        ):
            typer.echo("Source path was redirected. Select a local path and retry.", err=True)
            return False
        report = run_import(
            None, str(candidate.path), False, installed_version, source=candidate.source
        )
        imported, skipped, failed = report.imported, report.skipped, report.failed
        issue = report.terminal_error
    except Exception as error:
        typer.echo(
            f"Source failed ({error_category(error)}). Check the source and retry.", err=True
        )
        return False
    typer.echo(f"Conversations: imported {imported}, skipped {skipped}, failed {failed}.")
    if issue:
        typer.echo(f"Source failed ({issue}). Check the source and retry.", err=True)
    return not (issue or failed)


def import_selected() -> bool:
    try:
        candidates = discover(load_settings().chatgpt_export_inbox)
    except Exception:
        typer.echo("Could not discover local history. Check the profile and retry.", err=True)
        return False
    candidates = _unique([*candidates, *_manual_exports()])
    if not candidates:
        typer.echo("No eligible local history found. Import deferred.")
        return True
    for entry in candidates:
        typer.echo(f"{entry.source}: {entry.path}")
    selected = [
        entry
        for entry in candidates
        if typer.confirm(f"Select {entry.source} history at {entry.path}?", default=False)
    ]
    typer.echo(f"Sources skipped by user: {len(candidates) - len(selected)}.")
    if not selected or not typer.confirm("Import the selected local sources?", default=False):
        typer.echo("History import deferred.")
        return True
    complete = True
    installed_version = version("engineering-memory")
    for entry in selected:
        typer.echo(f"Importing {entry.source}: {entry.path}")
        if not _import_candidate(entry, installed_version):
            complete = False
    return complete
