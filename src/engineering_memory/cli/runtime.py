"""Composition root for operator commands; policies live behind boundaries."""

from contextlib import ExitStack
from pathlib import Path

from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.classification import (
    AliasProjectClassifier,
    ChainedProjectClassifier,
    ProjectRulesError,
    load_project_rules,
)
from engineering_memory.classification.metadata_classifier import MetadataProjectClassifier
from engineering_memory.ingestion.chatgpt import ChatGPTExportSource
from engineering_memory.ingestion.chatgpt.archive_source import ChatGPTArchiveSource
from engineering_memory.ingestion.claude_chat import ClaudeChatExportSource
from engineering_memory.ingestion.claude_chat.archive_source import ClaudeChatArchiveSource
from engineering_memory.ingestion.claude_code import ClaudeCodeSessionSource
from engineering_memory.ingestion.claude_code.archive_source import ClaudeCodeArchiveSource
from engineering_memory.ingestion.codex import CodexSessionSource
from engineering_memory.ingestion.codex.archive_source import CodexArchiveSource
from engineering_memory.ingestion.pipeline import IngestionPipeline
from engineering_memory.ingestion.report import Stage
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.ingestion.state import ImportStateCorrupt, ImportStateUnavailable
from engineering_memory.memory.hindsight.provision import ProvisionError
from engineering_memory.memory.hindsight.store import HindsightStore
from engineering_memory.memory.interface import MemoryStoreRejected, MemoryStoreUnavailable
from engineering_memory.observability.logging import configure
from engineering_memory.sanitization import PatternSecretSanitizer
from engineering_memory.settings import SettingsError, load_settings, load_state_path


def error_category(error: Exception) -> str:
    if isinstance(error, (SettingsError, ProjectRulesError)):
        return "configuration"
    if isinstance(error, (ImportStateCorrupt, ImportStateUnavailable)):
        return "state"
    if isinstance(error, (ProvisionError, MemoryStoreRejected, MemoryStoreUnavailable)):
        return "memory"
    return "internal"


def make_memory(settings):
    return HindsightStore(settings)


def run_import(
    data: dict,
    export: str | None,
    force: bool,
    version: str,
    *,
    dry_run: bool = False,
    source: str = "chatgpt",
) -> None:
    sources = {
        "chatgpt": (ChatGPTExportSource, ChatGPTArchiveSource),
        "claude-chat": (ClaudeChatExportSource, ClaudeChatArchiveSource),
        "claude-code": (ClaudeCodeSessionSource, ClaudeCodeArchiveSource),
        "codex": (CodexSessionSource, CodexArchiveSource),
    }
    export_reader, archive_reader = sources[source]
    settings = load_settings()
    configure(settings)
    rules = load_project_rules(
        settings.project_rules_path, required="project_rules_path" in settings.model_fields_set
    )
    with ExitStack() as resources:
        state = None
        if not dry_run or settings.import_state_path.exists():
            state = SQLiteImportState(settings.import_state_path, read_only=dry_run)
            resources.callback(state.close)
            if dry_run:
                state.validate()
            else:
                state.initialize()
        memory = None if dry_run else make_memory(settings.hindsight)
        if close := getattr(memory, "close", None):
            resources.callback(close)
        archive = LocalRawArchive(settings.archive_root)
        input_source = (
            export_reader(Path(export)) if export is not None else archive_reader(archive)
        )

        # Own the reader explicitly so interrupts/terminal failures release an open ZIP/export.
        class OwnedSource:
            source = input_source.source

            def read(self):
                reader = input_source.read()
                if close := getattr(reader, "close", None):
                    resources.callback(close)
                return reader

        report = IngestionPipeline(
            sanitizer=PatternSecretSanitizer(),
            classifier=ChainedProjectClassifier(
                (MetadataProjectClassifier(rules), AliasProjectClassifier(rules))
            ),
            archive=archive,
            memory=memory,
            state=state,
            importer_version=version,
            bank=settings.hindsight.bank_id,
        ).run(OwnedSource(), force=force, dry_run=dry_run)
        if dry_run:
            outcomes = []
            for outcome in report.outcomes:
                row = outcome.model_dump(
                    mode="json", exclude={"status", "completed_at", "state_record_failed"}
                )
                row["decision"] = {
                    "imported": "would_import",
                    "skipped": "would_skip",
                    "failed": "failed",
                }[outcome.status.value]
                outcomes.append(row)
            data.update(
                status=report.status.value,
                would_import=report.imported,
                would_skip=report.skipped,
                failed=report.failed,
                terminal_error=report.terminal_error,
                outcomes=outcomes,
            )
            return
        data.update(
            status=report.status.value,
            imported=report.imported,
            skipped=report.skipped,
            failed=report.failed,
            terminal_error=report.terminal_error,
            outcomes=[outcome.model_dump(mode="json") for outcome in report.outcomes],
        )


def run_status(data: dict) -> None:
    path = load_state_path()
    if not path.exists():
        return
    state = SQLiteImportState(path, read_only=True)
    try:
        state.validate()
        records = []
        for record in state.iter_records():
            row = record.model_dump(mode="json", exclude={"content_hash"})
            row["error"] = (
                record.error
                if record.error in set(Stage)
                else ("unknown" if record.error else None)
            )
            records.append(row)
        data.update(
            imported=sum(row["status"] == "imported" for row in records),
            failed=sum(row["status"] == "failed" for row in records),
            records=records,
        )
    finally:
        state.close()


def run_serve() -> None:
    """Compose reads only; the consumer owns the lifetime of this stdio child."""
    from engineering_memory.access.server import run_stdio
    from engineering_memory.access.service import MemoryAccess
    from engineering_memory.settings import load_access_settings

    settings = load_access_settings()
    with ExitStack() as resources:
        memory = make_memory(settings.hindsight)
        resources.callback(memory.close)
        run_stdio(MemoryAccess(memory, LocalRawArchive(settings.archive_root)))
