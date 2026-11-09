"""Acquisition lifecycle and metadata-only persistence contract."""

from datetime import UTC
from typing import Annotated, Literal, Protocol, Self

from pydantic import AwareDatetime, Field, field_validator, model_validator

from engineering_memory.ingestion.acquisition_source import Mode
from engineering_memory.normalization.base import FrozenModel

EvidenceKind = Literal["source_timestamp", "zip_member_estimate", "unknown"]


class AcquisitionRecord(FrozenModel):
    source: Literal["chatgpt"] = "chatgpt"
    digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    mode: Mode
    acquired_at: AwareDatetime
    produced_at: AwareDatetime | None
    production_evidence: EvidenceKind
    ingested_at: AwareDatetime | None = None

    @field_validator("acquired_at", "produced_at", "ingested_at")
    @classmethod
    def utc_dates(cls, value):
        return value.astimezone(UTC) if value is not None else None

    @model_validator(mode="after")
    def evidence_has_a_date(self) -> Self:
        if (self.produced_at is None) != (self.production_evidence == "unknown"):
            raise ValueError("production evidence and date disagree")
        return self


class AcquisitionState(Protocol):
    def find_acquisition(self, digest: str) -> AcquisitionRecord | None: ...

    def pending_acquisition(self) -> AcquisitionRecord | None: ...

    def latest_acquisition(self) -> AcquisitionRecord | None: ...

    def latest_production(self, evidence: EvidenceKind) -> AcquisitionRecord | None: ...

    def record_acquisition(self, record: AcquisitionRecord) -> None: ...

    def complete_acquisition(self, digest: str, ingested_at: AwareDatetime) -> None: ...
