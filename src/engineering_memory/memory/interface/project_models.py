"""Disposable project synthesis, separate from conversation retention and recall."""

from enum import StrEnum
from typing import Literal, Protocol

from pydantic import StrictBool, field_validator, model_validator

from engineering_memory.normalization import Provenance
from engineering_memory.normalization.base import FrozenModel, Slug, Text, Timestamp


class ModelKind(StrEnum):
    ARCHITECTURE = "architecture"
    STACK = "stack"
    DECISIONS = "decisions"


class ProjectModelKey(FrozenModel):
    project: Slug
    kind: ModelKind

    @field_validator("project")
    @classmethod
    def classified(cls, value):
        if value in {"unknown", "unclassified"}:
            raise ValueError("a classified project is required")
        return value


class ModelSupport(FrozenModel):
    document_id: Text
    provenance: Provenance

    @model_validator(mode="after")
    def identity(self):
        if self.document_id != f"{self.provenance.source.value}:{self.provenance.source_id}":
            raise ValueError("support identity mismatch")
        return self


class ProjectModelSnapshot(FrozenModel):
    content: Text
    refreshed_at: Timestamp
    supports: tuple[ModelSupport, ...]
    stale: StrictBool | None = None
    last_refresh_failed_at: Timestamp | None = None


class ProjectModelRead(FrozenModel):
    key: ProjectModelKey
    status: Literal["ready", "missing", "pending", "failed"]
    snapshot: ProjectModelSnapshot | None = None
    last_refresh_failed_at: Timestamp | None = None

    @model_validator(mode="after")
    def readiness(self):
        if (self.status == "ready") != (self.snapshot is not None):
            raise ValueError("inconsistent model readiness")
        return self


class RefreshOutcome(FrozenModel):
    key: ProjectModelKey
    status: Literal["completed", "pending", "failed", "unavailable"]
    refreshed_at: Timestamp | None = None
    error: Literal["rejected", "unavailable", "internal"] | None = None


class ProjectModelReader(Protocol):
    def get_project_model(self, key: ProjectModelKey) -> ProjectModelRead: ...


class ProjectModelMaintainer(Protocol):
    def refresh_project_model(self, key: ProjectModelKey) -> RefreshOutcome: ...
