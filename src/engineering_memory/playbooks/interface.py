"""Separate published reads from operator-only mutations."""

from collections.abc import Callable
from typing import Protocol

from engineering_memory.playbooks.models import ApprovedPlaybook, Draft, PlaybookContent, Summary


class CatalogUnavailable(RuntimeError):
    """The local catalog cannot be used."""


class PlaybookReader(Protocol):
    def list_approved(self, project: str, after_id: str | None, limit: int) -> list[Summary]: ...

    def get_approved(
        self, project: str, id: str, version: int | None
    ) -> ApprovedPlaybook | None: ...


class PlaybookWriter(Protocol):
    def stage(self, project: str, id: str, draft: Draft) -> None: ...

    def review(self, project: str, id: str) -> Draft | None: ...

    def approve(
        self, project: str, id: str, revision: str, verify: Callable[[PlaybookContent], None]
    ) -> int: ...
