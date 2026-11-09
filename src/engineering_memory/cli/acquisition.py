"""Compose the local acquisition adapters for a single operator invocation."""

from hashlib import sha256
from pathlib import Path

from engineering_memory.archive.export_blobs import LocalExportBlobs
from engineering_memory.cli.runtime import run_import
from engineering_memory.ingestion.acquisition import ExportAcquisition
from engineering_memory.ingestion.acquisition_intent import LocalAcquisitionIntent
from engineering_memory.ingestion.acquisition_lock import acquisition_lock
from engineering_memory.ingestion.acquisition_source import InboxExportSource, ManualExportSource
from engineering_memory.ingestion.report import RunReport
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.settings import SettingsError, load_settings


def run_acquisition(data: dict, file: str | None, version: str) -> None:
    settings = load_settings()
    path = settings.import_state_path.resolve()
    inbox = settings.chatgpt_export_inbox
    if file is None and inbox is None:
        raise SettingsError("configure a ChatGPT export inbox")

    def ingest(archive: Path) -> RunReport:
        return run_import(None, str(archive), False, version)

    def report(outcome: str, run: RunReport | None, digest: str | None) -> None:
        if run is None:
            if outcome != "duplicate" or data["outcome"] == "empty":
                data.update(outcome=outcome, digest=digest)
            return
        data.update(
            outcome=outcome,
            digest=digest,
            status=run.status.value,
            error=None if outcome == "imported" else "import_failed",
            terminal_error=run.terminal_error,
        )
        data["imported"] += run.imported
        data["skipped"] += run.skipped
        data["failed"] += run.failed

    with acquisition_lock(path) as acquired:
        if not acquired:
            data["outcome"] = "busy"
            return
        state = SQLiteImportState(path)

        def completed(digest: str) -> bool:
            record = state.find_acquisition(digest)
            return record is not None and record.ingested_at is not None

        if file is None:
            inbox_key = sha256(str(inbox).encode("utf-8")).hexdigest()[:16]
            observed = path.with_name(f"{path.name}.inbox-{inbox_key}.json")
            source = InboxExportSource(inbox, observed, completed)
            acknowledge = source.acknowledge
        else:
            source = ManualExportSource(Path(file))
            acknowledge = None
        try:
            ExportAcquisition(
                source=source,
                blobs=LocalExportBlobs(settings.archive_root),
                state=state,
                intent=LocalAcquisitionIntent(path.with_name(f"{path.name}.acquire-intent.json")),
                ingest=ingest,
                report=report,
                acknowledge=acknowledge,
                zip_offset_minutes=settings.chatgpt_export_zip_offset_minutes,
            ).run()
        finally:
            state.close()
