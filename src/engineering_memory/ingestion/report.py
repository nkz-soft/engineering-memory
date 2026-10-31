"""Safe immutable ingestion outcomes; process exit codes belong to the CLI."""

from enum import StrEnum

from pydantic import model_validator

from engineering_memory.ingestion.state import ImportStatus
from engineering_memory.normalization import Source
from engineering_memory.normalization.base import FrozenModel, OpaqueIdentifier, Timestamp


class Stage(StrEnum):
    """Fixed failure vocabulary: never copy arbitrary exception text into a report."""

    SOURCE = "source"
    HASH = "hash"
    STATE_READ = "state_read"
    SANITIZE = "sanitize"
    CLASSIFY = "classify"
    ENRICH = "enrich"
    ARCHIVE = "archive"
    RETAIN = "retain"
    STATE_WRITE = "state_write"


class RunStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"


class ConversationOutcome(FrozenModel):
    source: Source
    source_id: OpaqueIdentifier | None = None
    document_id: str | None = None
    status: ImportStatus
    completed_at: Timestamp
    error: Stage | None = None
    state_record_failed: bool = False

    @model_validator(mode="after")
    def _failure_has_diagnostics(self):
        if (self.status is ImportStatus.FAILED) != (self.error is not None):
            raise ValueError("only failed outcomes must carry an error")
        if self.state_record_failed and self.status is not ImportStatus.FAILED:
            raise ValueError("secondary state errors require a failed outcome")
        return self


class RunReport(FrozenModel):
    outcomes: tuple[ConversationOutcome, ...] = ()
    terminal_error: Stage | None = None

    @property
    def imported(self) -> int:
        return sum(item.status is ImportStatus.IMPORTED for item in self.outcomes)

    @property
    def skipped(self) -> int:
        return sum(item.status is ImportStatus.SKIPPED for item in self.outcomes)

    @property
    def failed(self) -> int:
        return sum(item.status is ImportStatus.FAILED for item in self.outcomes)

    @property
    def status(self) -> RunStatus:
        if not self.failed and self.terminal_error is None:
            return RunStatus.SUCCESS
        if self.imported or self.skipped:
            return RunStatus.PARTIAL_SUCCESS
        return RunStatus.FAILURE
