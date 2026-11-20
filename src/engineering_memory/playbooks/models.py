"""Validated input and persisted playbook records."""

from datetime import timedelta
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
)

from engineering_memory.normalization.base import Slug


def classified(value: str) -> str:
    if value in {"unknown", "unclassified"}:
        raise ValueError("a classified project is required")
    return value


def require_utc(value: AwareDatetime) -> AwareDatetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("a UTC timestamp is required")
    return value


def literal_text(value: str) -> str:
    if not value.strip() or any(not char.isprintable() and char not in "\n\t" for char in value):
        raise ValueError("invalid playbook text")
    return value


PlaybookID = Annotated[Slug, Field(max_length=200, strict=True)]
Project = Annotated[PlaybookID, AfterValidator(classified)]
Title = Annotated[StrictStr, Field(max_length=200), AfterValidator(literal_text)]
Step = Annotated[StrictStr, Field(max_length=2_000), AfterValidator(literal_text)]
Steps = Annotated[list[Step], Field(min_length=1, max_length=50)]
DocumentID = Annotated[StrictStr, Field(min_length=1, max_length=1024)]
Revision = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{32}$")]
Snapshot = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
Version = Annotated[StrictInt, Field(ge=1, le=2**63 - 1)]
UTCTimestamp = Annotated[AwareDatetime, AfterValidator(require_utc)]


class PlaybookModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlaybookKey(PlaybookModel):
    project: Project
    id: PlaybookID


class DraftInput(PlaybookModel):
    title: Title
    steps: Steps
    examples: Annotated[list[DocumentID], Field(min_length=1, max_length=10)]

    @field_validator("examples")
    @classmethod
    def unique_examples(cls, values: list[str]) -> list[str]:
        if len(set(values)) != len(values):
            raise ValueError("duplicate examples")
        return values


class Example(PlaybookModel):
    document_id: DocumentID
    project: Project
    source_timestamp: UTCTimestamp
    snapshot: Snapshot


class PlaybookContent(PlaybookModel):
    title: Title
    steps: Steps
    examples: Annotated[list[Example], Field(min_length=1, max_length=10)]


class Draft(PlaybookModel):
    revision: Revision
    content: PlaybookContent


class Summary(PlaybookModel):
    id: PlaybookID
    title: Title
    version: Version


class ApprovedPlaybook(PlaybookKey):
    version: Version
    latest_version: Version
    approved_at: UTCTimestamp
    content: PlaybookContent


class ListPlaybooksRequest(PlaybookModel):
    project: Project
    after_id: PlaybookID | None = None
    limit: Annotated[StrictInt, Field(ge=1, le=100)] = 20


class GetPlaybookRequest(PlaybookKey):
    version: Version | None = None
