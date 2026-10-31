"""Sequential, failure-isolated orchestration over replaceable boundaries."""

from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from time import perf_counter

from pydantic import TypeAdapter, ValidationError

from engineering_memory.archive.interface import RawArchive
from engineering_memory.classification.classifier import ProjectClassifier
from engineering_memory.ingestion.report import ConversationOutcome, RunReport, Stage
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
        memory: MemoryStore,
        state: ImportState,
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

    def run(self, source: ConversationSource, *, force: bool = False) -> RunReport:
        """Return outcomes in source order; cancellation propagates unchanged."""
        outcomes: list[ConversationOutcome] = []
        try:
            reader = iter(source.read())
        except Exception:
            return RunReport(terminal_error=Stage.SOURCE)
        while True:
            started_at = self.clock()
            started = perf_counter()
            try:
                item = next(reader)
            except StopIteration:
                break
            except SourceFormatError as error:
                outcome = ConversationOutcome(
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
                return RunReport(outcomes=tuple(outcomes), terminal_error=Stage.SOURCE)
            outcome, project = self._process(item, force=force)
            self._try_emit(outcome, project, started_at, started)
            outcomes.append(outcome)
        return RunReport(outcomes=tuple(outcomes))

    def _process(
        self, item: SourceConversation, *, force: bool
    ) -> tuple[ConversationOutcome, str | None]:
        conversation = item.conversation
        content_hash = None
        project = None
        stage = Stage.HASH
        try:
            content_hash = conversation.content_hash()
            stage = Stage.STATE_READ
            record = self.state.find(conversation.source, conversation.source_id)
            if may_skip(record, content_hash, force=force):
                return ConversationOutcome(
                    source=conversation.source,
                    source_id=conversation.source_id,
                    document_id=conversation.document_id,
                    status=ImportStatus.SKIPPED,
                    completed_at=self.clock(),
                ), None
            stage = Stage.SANITIZE
            sanitized, _ = self.sanitizer.sanitize(conversation)
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
            stage = Stage.ARCHIVE
            self.archive.store(enriched, item.original)
            stage = Stage.RETAIN
            self.memory.retain(enriched)
            stage = Stage.STATE_WRITE
            self.state.record(
                ImportRecord(
                    source=conversation.source,
                    source_id=conversation.source_id,
                    document_id=conversation.document_id,
                    content_hash=content_hash,
                    recorded_at=self.clock(),
                    status=ImportStatus.IMPORTED,
                )
            )
        except Exception:
            secondary = False
            if content_hash is not None:
                try:
                    self.state.record(
                        ImportRecord(
                            source=conversation.source,
                            source_id=conversation.source_id,
                            document_id=conversation.document_id,
                            content_hash=content_hash,
                            recorded_at=self.clock(),
                            status=ImportStatus.FAILED,
                            error=stage.value,
                        )
                    )
                except Exception:
                    secondary = True
            return ConversationOutcome(
                source=conversation.source,
                source_id=conversation.source_id,
                document_id=conversation.document_id,
                status=ImportStatus.FAILED,
                completed_at=self.clock(),
                error=stage,
                state_record_failed=secondary,
            ), project
        return ConversationOutcome(
            source=conversation.source,
            source_id=conversation.source_id,
            document_id=conversation.document_id,
            status=ImportStatus.IMPORTED,
            completed_at=self.clock(),
        ), project

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
        emit(
            "ingestion.operation",
            source=outcome.source.value,
            source_id=outcome.source_id,
            document_id=outcome.document_id,
            project=project,
            bank=self.bank,
            start_time=started_at.isoformat(),
            duration_ms=(perf_counter() - started) * 1000,
            status=outcome.status.value,
            error=outcome.error.value if outcome.error else None,
            state_record_failed=outcome.state_record_failed,
        )


def _usable_identity(subject: str | None) -> str | None:
    if subject is None:
        return None
    try:
        return TypeAdapter(OpaqueIdentifier).validate_python(subject)
    except ValidationError:
        return None
