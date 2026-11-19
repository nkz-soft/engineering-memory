"""Bounded, content-free observations for operator status."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator

from engineering_memory.ingestion.report import RunReport, RunStatus, Stage
from engineering_memory.normalization import Source
from engineering_memory.normalization.base import FrozenModel, Timestamp

STATUS_SOURCES = (Source.CHATGPT, Source.CLAUDE_CHAT, Source.CLAUDE_CODE, Source.CODEX)
ERROR_CATEGORIES = frozenset(Stage) | {"configuration", "state", "memory", "internal", "unknown"}


class SourceHealth(FrozenModel):
    source: Source
    outcome: Literal["healthy", "waiting", "partial", "failed", "unobserved"] = "unobserved"
    last_attempt_at: Timestamp | None = None
    last_success_at: Timestamp | None = None
    deferred_count: Annotated[int, Field(ge=0)] = 0
    error_categories: tuple[str, ...] = ()

    @field_validator("error_categories")
    @classmethod
    def allowlisted_categories(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        categories = {value if value in ERROR_CATEGORIES else "unknown" for value in values}
        return tuple(sorted(categories))

    @classmethod
    def from_report(
        cls, source: Source, report: RunReport, completed_at: datetime, *, deferred: int = 0
    ) -> "SourceHealth":
        errors = {item.error for item in report.outcomes if item.error is not None}
        if report.terminal_error is not None:
            errors.add(report.terminal_error)
        if any(item.state_record_failed for item in report.outcomes):
            errors.add(Stage.STATE_WRITE)
        return cls(
            source=source,
            outcome={
                RunStatus.SUCCESS: "waiting" if deferred and not report.imported else "healthy",
                RunStatus.PARTIAL_SUCCESS: "partial",
                RunStatus.FAILURE: "failed",
            }[report.status],
            last_attempt_at=completed_at,
            deferred_count=deferred,
            error_categories=tuple(errors),
        )


class ProjectImportEvidence(FrozenModel):
    """Bounds on when confirmed imports could have reached the memory service."""

    started_at: Timestamp
    completed_at: Timestamp
