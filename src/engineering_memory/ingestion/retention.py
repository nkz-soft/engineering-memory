"""Durable receipt bookkeeping for the asynchronous retain capability."""

from enum import StrEnum
from typing import Protocol

from engineering_memory.ingestion.state import ImportRecord
from engineering_memory.normalization import Source
from engineering_memory.normalization.base import (
    FrozenModel,
    OpaqueIdentifier,
    Slug,
    Text,
    Timestamp,
)


class RetainStatus(StrEnum):
    PENDING = "pending"
    UNCERTAIN = "uncertain"


class RetainReceipt(FrozenModel):
    source: Source
    source_id: OpaqueIdentifier
    document_id: Text
    content_hash: Text
    token: Text
    project: Slug
    started_at: Timestamp
    accepted: bool

    @property
    def status(self) -> RetainStatus:
        return RetainStatus.PENDING if self.accepted else RetainStatus.UNCERTAIN


class RetainJournal(Protocol):
    def pending_retains(self, source: Source | None = None) -> list[RetainReceipt]: ...

    def checkpoint_retain(self, receipt: RetainReceipt) -> None: ...

    def finish_retain(self, receipt: RetainReceipt, record: ImportRecord) -> None: ...
