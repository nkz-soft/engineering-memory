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
from engineering_memory.ingestion.retention import RetainJournal, RetainReceipt, RetainStatus
from engineering_memory.ingestion.source import (
    ConversationSource,
    SourceConversation,
    SourceFormatError,
)
from engineering_memory.ingestion.state import (
    ImportRecord,
    ImportState,
    ImportStateCorrupt,
    ImportStateUnavailable,
    ImportStatus,
    may_skip,
)
from engineering_memory.memory.interface import (
    MemoryStore,
    MemoryStoreRejected,
    MemoryStoreUnavailable,
    RetainProgress,
    TrackedRetain,
)
from engineering_memory.normalization import EnrichedConversation
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
        record_import: Callable[[ImportRecord, str, datetime], None] | None = None,
        retain_journal: RetainJournal | None = None,
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
        self.record_import = record_import
        self.retain_journal = retain_journal
        self.tracked_memory = memory if isinstance(memory, TrackedRetain) else None

    def run(
        self,
        source: ConversationSource,
        *,
        force: bool = False,
        dry_run: bool = False,
        reconcile_missing: bool = True,
    ) -> RunReport:
        """Return outcomes in source order; cancellation propagates unchanged."""
        if not dry_run and (self.memory is None or self.state is None):
            raise ValueError("real ingestion requires memory and state adapters")
        outcomes: list[ConversationOutcome] = []
        report_type = PreviewReport if dry_run else RunReport
        outcome_type = PreviewOutcome if dry_run else ConversationOutcome
        overlay = {} if dry_run else None
        handled_retains: set[str] = set()
        receipts: dict[str, RetainReceipt] = {}
        if not dry_run and self.retain_journal is not None:
            try:
                receipts = {
                    receipt.source_id: receipt
                    for receipt in self.retain_journal.pending_retains(source.source)
                }
            except Exception:
                return report_type(terminal_error=Stage.STATE_READ)
        terminal_error = None
        try:
            reader = iter(source.read())
        except Exception:
            terminal_error = Stage.SOURCE
            reader = iter(())
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
                terminal_error = Stage.SOURCE
                break
            source_id = item.conversation.source_id
            if source_id in handled_retains:
                continue
            receipt = receipts.pop(source_id, None)
            outcome, project = self._process(item, force=force, overlay=overlay, receipt=receipt)
            if receipt is not None or _retain_unresolved(outcome):
                handled_retains.add(source_id)
            self._try_emit(outcome, project, started_at, started)
            outcomes.append(outcome)
        if reconcile_missing:
            for receipt in receipts.values():
                started_at, started = self.clock(), perf_counter()
                outcome = self._reconcile_retain(receipt)
                self._try_emit(outcome, receipt.project, started_at, started)
                outcomes.append(outcome)
        return report_type(outcomes=tuple(outcomes), terminal_error=terminal_error)

    def _process(
        self,
        item: SourceConversation,
        *,
        force: bool,
        overlay: dict | None = None,
        receipt: RetainReceipt | None = None,
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
            if receipt is not None:
                outcome = self._reconcile_retain(receipt)
                if receipt.content_hash == content_hash or _retain_unresolved(outcome):
                    return outcome, receipt.project
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
                repository=sanitized.repository or self.repository,
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
                if self.tracked_memory is not None and self.retain_journal is not None:
                    return self._submit_retain(enriched, content_hash, project), project
                self.memory.retain(enriched)
            stage = Stage.STATE_WRITE
            retained = ImportRecord(
                source=conversation.source,
                source_id=conversation.source_id,
                document_id=conversation.document_id,
                content_hash=content_hash,
                recorded_at=self.clock(),
                status=ImportStatus.IMPORTED,
            )
            if not preview and self.record_import is not None:
                self.record_import(retained, project, enriched.provenance.imported_at)
            else:
                self._remember(overlay, retained)
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

    def _submit_retain(
        self, enriched: EnrichedConversation, content_hash: str, project: str
    ) -> ConversationOutcome:
        conversation = enriched.conversation
        receipt = None

        def checkpoint(token: str, accepted: bool) -> None:
            nonlocal receipt
            receipt = RetainReceipt(
                source=conversation.source,
                source_id=conversation.source_id,
                document_id=conversation.document_id,
                content_hash=content_hash,
                token=token,
                project=project,
                started_at=enriched.provenance.imported_at,
                accepted=accepted,
            )
            self.retain_journal.checkpoint_retain(receipt)

        try:
            progress = self.tracked_memory.retain_tracked(enriched, checkpoint)
        except Exception as error:
            if receipt is None:
                raise
            if isinstance(error, (ImportStateCorrupt, ImportStateUnavailable)):
                return self._receipt_outcome(receipt, ImportStatus.FAILED, Stage.STATE_WRITE)
            return self._receipt_outcome(receipt, receipt.status)
        return self._settle_retain(receipt, progress)

    def _reconcile_retain(self, receipt: RetainReceipt) -> ConversationOutcome:
        progress = RetainProgress.UNKNOWN
        if self.tracked_memory is not None:
            with suppress(MemoryStoreRejected, MemoryStoreUnavailable):
                progress = self.tracked_memory.check_retain(receipt.token)
        return self._settle_retain(receipt, progress)

    def _settle_retain(
        self, receipt: RetainReceipt, progress: RetainProgress
    ) -> ConversationOutcome:
        try:
            if progress is RetainProgress.PENDING and not receipt.accepted:
                receipt = receipt.model_copy(update={"accepted": True})
                self.retain_journal.checkpoint_retain(receipt)
            if progress in (RetainProgress.UNKNOWN, RetainProgress.PENDING):
                return self._receipt_outcome(receipt, receipt.status)

            success = progress is RetainProgress.COMPLETED
            status = ImportStatus.IMPORTED if success else ImportStatus.FAILED
            error = None if success else Stage.RETAIN
            outcome = self._receipt_outcome(receipt, status, error)
            self.retain_journal.finish_retain(
                receipt,
                ImportRecord(
                    source=receipt.source,
                    source_id=receipt.source_id,
                    document_id=receipt.document_id,
                    content_hash=receipt.content_hash,
                    recorded_at=outcome.completed_at,
                    status=status,
                    error=error,
                ),
            )
            return outcome
        except Exception:
            return self._receipt_outcome(receipt, ImportStatus.FAILED, Stage.STATE_WRITE)

    def _receipt_outcome(
        self,
        receipt: RetainReceipt,
        status: ImportStatus | RetainStatus,
        error: Stage | None = None,
    ) -> ConversationOutcome:
        return ConversationOutcome(
            source=receipt.source,
            source_id=receipt.source_id,
            document_id=receipt.document_id,
            status=status,
            completed_at=self.clock(),
            error=error,
        )

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


def _retain_unresolved(outcome: ConversationOutcome) -> bool:
    return isinstance(outcome.status, RetainStatus) or outcome.error is Stage.STATE_WRITE


def _usable_identity(subject: str | None) -> str | None:
    if subject is None:
        return None
    try:
        return TypeAdapter(OpaqueIdentifier).validate_python(subject)
    except ValidationError:
        return None
