"""Composition root for operator commands; policies live behind boundaries."""

from contextlib import ExitStack
from datetime import UTC, datetime
from ipaddress import ip_address
from pathlib import Path

from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.classification import (
    AliasProjectClassifier,
    ChainedProjectClassifier,
    ProjectRulesError,
    load_project_rules,
)
from engineering_memory.classification.metadata_classifier import MetadataProjectClassifier
from engineering_memory.ingestion.acquisition_source import AcquisitionError
from engineering_memory.ingestion.chatgpt import ChatGPTExportSource
from engineering_memory.ingestion.chatgpt.archive_source import ChatGPTArchiveSource
from engineering_memory.ingestion.claude_chat import ClaudeChatExportSource
from engineering_memory.ingestion.claude_chat.archive_source import ClaudeChatArchiveSource
from engineering_memory.ingestion.claude_code import ClaudeCodeSessionSource
from engineering_memory.ingestion.claude_code.archive_source import ClaudeCodeArchiveSource
from engineering_memory.ingestion.codex import CodexSessionSource
from engineering_memory.ingestion.codex.archive_source import CodexArchiveSource
from engineering_memory.ingestion.health import SourceHealth
from engineering_memory.ingestion.pipeline import IngestionPipeline
from engineering_memory.ingestion.report import RunReport, Stage
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.ingestion.state import ImportStateCorrupt, ImportStateUnavailable
from engineering_memory.memory.hindsight.provision import ProvisionError
from engineering_memory.memory.hindsight.store import HindsightStore
from engineering_memory.memory.interface import MemoryStoreRejected, MemoryStoreUnavailable
from engineering_memory.observability.logging import configure
from engineering_memory.sanitization import PatternSecretSanitizer
from engineering_memory.settings import SettingsError, load_settings, load_state_path


def error_category(error: Exception) -> str:
    if isinstance(error, AcquisitionError):
        return str(error)
    if isinstance(error, (SettingsError, ProjectRulesError)):
        return "configuration"
    if isinstance(error, (ImportStateCorrupt, ImportStateUnavailable)):
        return "state"
    if isinstance(error, (ProvisionError, MemoryStoreRejected, MemoryStoreUnavailable)):
        return "memory"
    return "internal"


def make_memory(settings):
    return HindsightStore(settings)


def make_project_models(settings):
    from engineering_memory.memory.hindsight.project_models import HindsightProjectModels

    return HindsightProjectModels(settings)


def run_model_refresh(data, keys):
    from engineering_memory.ingestion.project_models import refresh_project_models
    from engineering_memory.settings import load_access_settings

    settings = load_access_settings()
    models = make_project_models(settings.hindsight)
    try:
        outcomes = refresh_project_models(models, keys)
        completed = sum(outcome.status == "completed" for outcome in outcomes)
        data.update(
            project=keys[0].project,
            status="success" if completed == len(keys) else "partial" if completed else "failure",
            models=[
                {"kind": outcome.key.kind.value, **outcome.model_dump(mode="json", exclude={"key"})}
                for outcome in outcomes
            ],
        )
    finally:
        models.close()


def _import_pipeline(
    settings, version, resources, *, dry_run=False
) -> tuple[IngestionPipeline, SQLiteImportState | None]:
    configure(settings)
    rules = load_project_rules(
        settings.project_rules_path, required="project_rules_path" in settings.model_fields_set
    )
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
    pipeline = IngestionPipeline(
        sanitizer=PatternSecretSanitizer(),
        classifier=ChainedProjectClassifier(
            (MetadataProjectClassifier(rules), AliasProjectClassifier(rules))
        ),
        archive=archive,
        memory=memory,
        state=state,
        importer_version=version,
        bank=settings.hindsight.bank_id,
        record_import=state.record_import if state is not None and not dry_run else None,
    )
    return pipeline, state


def run_import(
    data: dict | None,
    export: str | None,
    force: bool,
    version: str,
    *,
    dry_run: bool = False,
    source: str = "chatgpt",
) -> RunReport:
    sources = {
        "chatgpt": (ChatGPTExportSource, ChatGPTArchiveSource),
        "claude-chat": (ClaudeChatExportSource, ClaudeChatArchiveSource),
        "claude-code": (ClaudeCodeSessionSource, ClaudeCodeArchiveSource),
        "codex": (CodexSessionSource, CodexArchiveSource),
    }
    export_reader, archive_reader = sources[source]
    settings = load_settings()
    with ExitStack() as resources:
        pipeline, state = _import_pipeline(settings, version, resources, dry_run=dry_run)
        input_source = (
            export_reader(Path(export)) if export is not None else archive_reader(pipeline.archive)
        )

        # Own the reader explicitly so interrupts/terminal failures release an open ZIP/export.
        class OwnedSource:
            source = input_source.source

            def read(self):
                reader = input_source.read()
                if close := getattr(reader, "close", None):
                    resources.callback(close)
                return reader

        report = pipeline.run(OwnedSource(), force=force, dry_run=dry_run)
        if dry_run:
            if data is None:
                return report
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
            return report
        if data is not None:
            data.update(
                status=report.status.value,
                imported=report.imported,
                skipped=report.skipped,
                failed=report.failed,
                terminal_error=report.terminal_error,
                outcomes=[outcome.model_dump(mode="json") for outcome in report.outcomes],
            )
        assert state is not None
        state.record_attempt(
            SourceHealth.from_report(OwnedSource.source, report, datetime.now(UTC))
        )
        return report


def run_session_import(data: dict, version: str) -> None:
    from engineering_memory.cli.session_lock import CaptureBusy, capture_lock
    from engineering_memory.ingestion.session_capture import CapturedSessionSource

    settings = load_settings()
    capture = settings.session_import
    roots = {"codex": capture.codex_root, "claude-code": capture.claude_code_root}
    if all(root is None for root in roots.values()):
        data.update(status="failure", error="configuration")
        return

    attempt_write_failed = False
    try:
        with capture_lock(settings.import_state_path), ExitStack() as resources:
            pipeline, state = _import_pipeline(settings, version, resources)
            assert state is not None
            for kind, root in roots.items():
                if root is None:
                    continue
                source = CapturedSessionSource(kind, root, capture.quiet_seconds)
                report = pipeline.run(source)
                observation = SourceHealth.from_report(
                    source.source,
                    report,
                    datetime.now(UTC),
                    deferred=source.deferred,
                )
                try:
                    state.record_attempt(observation)
                except (ImportStateUnavailable, ImportStateCorrupt):
                    attempt_write_failed = True
                data["sources"].append(
                    {
                        "source": kind,
                        "imported": report.imported,
                        "unchanged": report.skipped,
                        "deferred": source.deferred,
                        "failed": report.failed,
                        "error": "source_unavailable" if report.terminal_error else None,
                    }
                )
    except CaptureBusy:
        data.update(status="failure", error="busy")
        return

    rows = data["sources"]
    if attempt_write_failed:
        data["error"] = "state"
    if attempt_write_failed or any(row["failed"] or row["error"] for row in rows):
        data["status"] = (
            "partial_success"
            if any(row["imported"] or row["unchanged"] for row in rows)
            else "failure"
        )


def run_status(data: dict) -> None:
    path = load_state_path()
    if not path.exists():
        return
    state = SQLiteImportState(path, read_only=True)
    try:
        state.validate()
        if (last := state.latest_acquisition()) is not None:
            data["last_chatgpt_export"] = last.model_dump(
                mode="json", include={"produced_at", "production_evidence", "ingested_at"}
            )
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


def read_session_handoff(
    *, document_id: str, project: str, link_origin: str | None
) -> dict[str, str]:
    from engineering_memory.access.handoff import session_handoff
    from engineering_memory.access.synthesis import OpenAICompatibleSynthesizer
    from engineering_memory.settings import load_archive_access_settings

    settings = load_archive_access_settings()
    synthesis = OpenAICompatibleSynthesizer(settings.deep_recall) if settings.deep_recall else None
    return session_handoff(
        LocalRawArchive(settings.archive_root),
        synthesis,
        document_id=document_id,
        project=project,
        link_origin=link_origin,
    )


def make_read_access(resources: ExitStack, *, include_models: bool = False):
    from engineering_memory.access.service import MemoryAccess
    from engineering_memory.access.synthesis import OpenAICompatibleSynthesizer
    from engineering_memory.settings import load_access_settings

    settings = load_access_settings()
    memory = make_memory(settings.hindsight)
    resources.callback(memory.close)
    models = None
    if include_models:
        models = make_project_models(settings.hindsight)
        resources.callback(models.close)
    synthesis = OpenAICompatibleSynthesizer(settings.deep_recall) if settings.deep_recall else None
    return MemoryAccess(
        memory,
        LocalRawArchive(settings.archive_root),
        models=models,
        reflection=memory,
        synthesis=synthesis,
        handoff_synthesis=synthesis,
    )


def make_explorer_status(resources: ExitStack):
    from engineering_memory.access.status import ExplorerStatus
    from engineering_memory.settings import load_access_settings

    settings = load_access_settings().hindsight
    models = make_project_models(settings)
    resources.callback(models.close)
    host = (settings.base_url.host or "").strip("[]")
    try:
        comparable_clocks = ip_address(host).is_loopback
    except ValueError:
        comparable_clocks = host.lower().rstrip(".") == "localhost"
    return ExplorerStatus(_read_import_health, models, comparable_clocks=comparable_clocks)


def _read_import_health(project: str | None):
    try:
        path = load_state_path()
        path.stat()
    except FileNotFoundError:
        return [], None
    except (OSError, SettingsError):
        raise ImportStateUnavailable("import status is unavailable") from None
    state = SQLiteImportState(path, read_only=True)
    try:
        state.validate()
        return state.read_health(project)
    finally:
        state.close()


def run_serve() -> None:
    """Compose reads only; the consumer owns the lifetime of this stdio child."""
    from engineering_memory.access.server import run_stdio

    with ExitStack() as resources:
        run_stdio(make_read_access(resources, include_models=True))
