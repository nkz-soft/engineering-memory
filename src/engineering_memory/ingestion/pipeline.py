"""Sequential, failure-isolated orchestration over replaceable boundaries."""

from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from time import perf_counter

from pydantic import TypeAdapter, ValidationError

from engineering_memory.archive.interface import RawArchive
from engineering_memory.classification.classifier import ProjectClassifier
from engineering_memory.ingestion.report import (
    ConversationOutcome,
    PreviewOutcome,
    PreviewReport,
    RunReport,
    Stage,
)
from engineering_memory.ingestion.source import (
    ConversationSource,
    SourceConversation,
    SourceFormatError,
)
from engineering_memory.ingestion.state import ImportRecord, ImportState, ImportStatus, may_skip
from engineering_memory.memory.interface import MemoryStore
from engineering_memory.normalization.base import OpaqueIdentifier
from engineering_memory.normalization.enrichment import enrich
from engineering_memory.observability.logging import get_logger
from engineering_memory.sanitization.sanitizer import SecretSanitizer


def _utc_now() -> datetime:
    return datetime.now(UTC)


class IngestionPipeline:
    """The caller owns adapter setup/lifetime; one run has one state writer.

    Adapters own transport retries. This layer never retries a whole conversation
    inside a run, and never sends a document to memory before archiving both forms.
    """

    def __init__(
        self,
        *,
        sanitizer: SecretSanitizer,
        classifier: ProjectClassifier,
        archive: RawArchive,
        memory: MemoryStore | None,
        state: ImportState | None,
        importer_version: str,
        bank: str = "engineering-global",
        repository: str | None = None,
        user: str | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.sanitizer = sanitizer
        self.classifier = classifier
        self.archive = archive
        self.memory = memory
        self.state = state
        self.importer_version = importer_version
        self.bank = bank
        self.repository = repository
        self.user = user
        self.clock = clock

    def run(
        self, source: ConversationSource, *, force: bool = False, dry_run: bool = False
    ) -> RunReport:
        """Return outcomes in source order; cancellation propagates unchanged."""
        if not dry_run and (self.memory is None or self.state is None):
            raise ValueError("real ingestion requires memory and state adapters")
        outcomes: list[ConversationOutcome] = []
        report_type = PreviewReport if dry_run else RunReport
        outcome_type = PreviewOutcome if dry_run else ConversationOutcome
        overlay = {} if dry_run else None
        try:
            reader = iter(source.read())
        except Exception:
            return report_type(terminal_error=Stage.SOURCE)
        while True:
            started_at = self.clock()
            started = perf_counter()
            try:
                item = next(reader)
            except StopIteration:
                break
            except SourceFormatError as error:
                outcome = outcome_type(
                    source=source.source,
                    source_id=_usable_identity(error.subject),
                    status=ImportStatus.FAILED,
                    completed_at=self.clock(),
                    error=Stage.SOURCE,
                )
                self._try_emit(outcome, None, started_at, started)
                outcomes.append(outcome)
                continue
            except Exception:
                return report_type(outcomes=tuple(outcomes), terminal_error=Stage.SOURCE)
            outcome, project = self._process(item, force=force, overlay=overlay)
            self._try_emit(outcome, project, started_at, started)
            outcomes.append(outcome)
        return report_type(outcomes=tuple(outcomes))

    def _process(
        self, item: SourceConversation, *, force: bool, overlay: dict | None = None
    ) -> tuple[ConversationOutcome, str | None]:
        conversation = item.conversation
        content_hash = None
        project = None
        stage = Stage.HASH
        preview = overlay is not None
        metadata = {}
        skipped = False
        outcome_type = PreviewOutcome if preview else ConversationOutcome
        key = (conversation.source, conversation.source_id)
        try:
            content_hash = conversation.content_hash()
            stage = Stage.STATE_READ
            record = (
                overlay[key]
                if preview and key in overlay
                else (
                    self.state.find(conversation.source, conversation.source_id)
                    if self.state is not None
                    else None
                )
            )
            skipped = may_skip(record, content_hash, force=force)
            if skipped and not preview:
                return outcome_type(
                    source=conversation.source,
                    source_id=conversation.source_id,
                    document_id=conversation.document_id,
                    status=ImportStatus.SKIPPED,
                    completed_at=self.clock(),
                ), None
            stage = Stage.SANITIZE
            sanitized, redactions = self.sanitizer.sanitize(conversation)
            stage = Stage.CLASSIFY
            tag = self.classifier.classify(sanitized)
            project = tag.value
            stage = Stage.ENRICH
            enriched = enrich(
                sanitized,
                tag,
                importer_version=self.importer_version,
                imported_at=self.clock(),
                repository=self.repository,
                user=self.user,
            )
            if preview:
                metadata = dict(
                    project=str(tag),
                    timestamp=enriched.conversation.started_at,
                    redaction_categories=tuple(sorted(redactions.counts)),
                )
            stage = Stage.ARCHIVE
            if not preview:
                self.archive.store(enriched, item.original)
            stage = Stage.RETAIN
            if not preview:
                self.memory.retain(enriched)
            stage = Stage.STATE_WRITE
            self._remember(
                overlay,
                ImportRecord(
                    source=conversation.source,
                    source_id=conversation.source_id,
                    document_id=conversation.document_id,
                    content_hash=content_hash,
                    recorded_at=self.clock(),
                    status=ImportStatus.IMPORTED,
                ),
            )
        except Exception:
            secondary = False
            if content_hash is not None and not (preview and skipped):
                try:
                    self._remember(
                        overlay,
                        ImportRecord(
                            source=conversation.source,
                            source_id=conversation.source_id,
                            document_id=conversation.document_id,
                            content_hash=content_hash,
                            recorded_at=self.clock(),
                            status=ImportStatus.FAILED,
                            error=stage.value,
                        ),
                    )
                except Exception:
                    secondary = True
            return outcome_type(
                source=conversation.source,
                source_id=conversation.source_id,
                document_id=conversation.document_id,
                status=ImportStatus.FAILED,
                completed_at=self.clock(),
                error=stage,
                state_record_failed=secondary,
                **metadata,
            ), project
        return outcome_type(
            source=conversation.source,
            source_id=conversation.source_id,
            document_id=conversation.document_id,
            status=ImportStatus.SKIPPED if skipped else ImportStatus.IMPORTED,
            completed_at=self.clock(),
            **metadata,
        ), project

    def _remember(self, overlay: dict | None, record: ImportRecord) -> None:
        if overlay is not None:
            overlay[(record.source, record.source_id)] = record
        else:
            self.state.record(record)

    def _try_emit(
        self,
        outcome: ConversationOutcome,
        project: str | None,
        started_at: datetime,
        started: float,
    ) -> None:
        # A broken diagnostic sink must not prevent processing or lose the report.
        # Do not attempt to log this failure back through the same sink.
        with suppress(Exception):
            self._emit(outcome, project, started_at, started)

    def _emit(
        self,
        outcome: ConversationOutcome,
        project: str | None,
        started_at: datetime,
        started: float,
    ) -> None:
        # Use the shared logger and event schema directly. The operation context
        # formats raw exception text, which untrusted adapters may fill with content.
        logger = get_logger()
        emit = logger.error if outcome.status is ImportStatus.FAILED else logger.info
        preview = isinstance(outcome, PreviewOutcome)
        status = outcome.status.value
        if preview and outcome.status is not ImportStatus.FAILED:
            status = "would_import" if outcome.status is ImportStatus.IMPORTED else "would_skip"
        emit(
            "ingestion.operation",
            source=outcome.source.value,
            source_id=outcome.source_id,
            document_id=outcome.document_id,
            project=project,
            bank=self.bank,
            start_time=started_at.isoformat(),
            duration_ms=(perf_counter() - started) * 1000,
            status=status,
            error=outcome.error.value if outcome.error else None,
            state_record_failed=outcome.state_record_failed,
            **({"dry_run": True} if preview else {}),
        )


def _usable_identity(subject: str | None) -> str | None:
    if subject is None:
        return None
    try:
        return TypeAdapter(OpaqueIdentifier).validate_python(subject)
    except ValidationError:
        return None
