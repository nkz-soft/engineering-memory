"""Private inputs and paired outcomes for the reflection evaluation."""

from collections import Counter
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, TypeAdapter, model_validator

from engineering_memory.evaluation.benchmark import (
    RECALL_LIMIT,
    EvaluationModel,
    Limit,
    Nonblank,
    VersionOne,
    _require_unique,
)
from engineering_memory.evaluation.reports import PublicID
from engineering_memory.normalization import Provenance, Source
from engineering_memory.normalization.base import OpaqueIdentifier, Slug, Text, Timestamp

CaseKind = Literal["evolution", "decision", "lookup"]
Operation = Literal["search_memory", "reflect"]
Failure = Literal["tool_error", "invalid_response", "timeout", "transport"]
PrivateText = Annotated[Text, Field(pattern=r"\S")]
_NATIVE_ID = TypeAdapter(OpaqueIdentifier)


def _classified(value: str) -> str:
    if value in {"unknown", "unclassified"}:
        raise ValueError("a classified project is required")
    return value


def _document_id(value: str) -> str:
    source, native = value.split(":", 1)
    Source(source)
    _NATIVE_ID.validate_python(native)
    if any(part in native for part in ("/", "\\", "..")):
        raise ValueError("invalid evidence reference")
    return value


ProjectKey = Annotated[Slug, AfterValidator(_classified)]
DocumentID = Annotated[Nonblank, AfterValidator(_document_id)]


class ReflectProfile(EvaluationModel):
    engine_version: PrivateText
    model_id: PrivateText
    corpus_summary: PrivateText
    project_model_availability: dict[ProjectKey, bool]


class ExpectedPoint(EvaluationModel):
    id: PublicID
    text: PrivateText
    document_ids: Annotated[list[DocumentID], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        _require_unique(self.document_ids, "expected document ID")
        return self


class ReflectCase(EvaluationModel):
    id: PublicID
    kind: CaseKind
    project: ProjectKey
    question: PrivateText
    expected_points: Annotated[list[ExpectedPoint], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_points(self) -> Self:
        _require_unique([point.id for point in self.expected_points], "expected point ID")
        return self


class ReflectCaseSet(EvaluationModel):
    schema_version: VersionOne
    version: PublicID
    profile: ReflectProfile
    cases: list[ReflectCase]

    @model_validator(mode="after")
    def validate_cases(self) -> Self:
        _require_unique([case.id for case in self.cases], "case ID")
        counts = Counter(case.kind for case in self.cases)
        if (
            not counts["evolution"]
            or not counts["decision"]
            or counts["evolution"] + counts["decision"] < 6
            or counts["lookup"] < 2
        ):
            raise ValueError("case set needs both synthesis kinds and lookup controls")
        if (
            not {case.project for case in self.cases}
            <= self.profile.project_model_availability.keys()
        ):
            raise ValueError("missing project model availability")
        return self


class Citation(EvaluationModel):
    document_id: DocumentID
    provenance: Provenance
    started_at: Annotated[Timestamp, Field(strict=False)]

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        provenance = self.provenance
        if self.document_id != f"{provenance.source.value}:{provenance.source_id}":
            raise ValueError("invalid citation identity")
        return self


class SearchEvidence(Citation):
    content: Text
    score: float | None


class SearchResponse(EvaluationModel):
    results: Annotated[list[SearchEvidence], Field(max_length=RECALL_LIMIT)]


class ReflectResponse(EvaluationModel):
    status: Literal["completed", "insufficient_evidence"]
    answer: PrivateText | None = None
    references: list[Citation]

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        _require_unique([ref.document_id for ref in self.references], "reference")
        completed = self.status == "completed"
        if completed != bool(self.references) or completed != (self.answer is not None):
            raise ValueError("inconsistent reflection result")
        return self


class OperationOutcome(EvaluationModel):
    operation: Operation
    status: Literal["completed", "insufficient_evidence", "failed", "unattempted"]
    elapsed_ms: float | None = None
    results: list[SearchEvidence] | None = None
    answer: PrivateText | None = None
    references: list[Citation] | None = None
    failure: Failure | None = None


class PairedResult(EvaluationModel):
    case_id: PublicID
    kind: CaseKind
    search_memory: OperationOutcome
    reflect: OperationOutcome


class ReflectRun(EvaluationModel):
    schema_version: VersionOne = 1
    case_set_version: PublicID
    started_at: datetime
    profile: ReflectProfile
    recall_limit: Limit = RECALL_LIMIT
    status: Literal["complete", "incomplete"]
    failure: Literal["transport"] | None = None
    pairs: list[PairedResult]

    @property
    def has_errors(self) -> bool:
        return self.status == "incomplete" or any(
            "failed" in (pair.search_memory.status, pair.reflect.status) for pair in self.pairs
        )
