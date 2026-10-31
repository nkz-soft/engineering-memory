"""Composition root for operator commands; policies live behind boundaries."""

from contextlib import ExitStack
from pathlib import Path

from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.classification import (
    AliasProjectClassifier,
    ProjectRulesError,
    load_project_rules,
)
from engineering_memory.ingestion.chatgpt import ChatGPTExportSource
from engineering_memory.ingestion.chatgpt.archive_source import ChatGPTArchiveSource
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


def run_import(data: dict, export: str | None, force: bool, version: str) -> None:
    settings = load_settings()
    configure(settings)
    rules = load_project_rules(
        settings.project_rules_path, required="project_rules_path" in settings.model_fields_set
    )
    with ExitStack() as resources:
        state = SQLiteImportState(settings.import_state_path)
        resources.callback(state.close)
        state.initialize()
        memory = make_memory(settings.hindsight)
        if close := getattr(memory, "close", None):
            resources.callback(close)
        archive = LocalRawArchive(settings.archive_root)
        input_source = (
            ChatGPTExportSource(Path(export))
            if export is not None
            else ChatGPTArchiveSource(archive)
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
            classifier=AliasProjectClassifier(rules),
            archive=archive,
            memory=memory,
            state=state,
            importer_version=version,
            bank=settings.hindsight.bank_id,
        ).run(OwnedSource(), force=force)
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
