"""Read-only operational metadata for the local explorer."""

from collections.abc import Callable

from engineering_memory.ingestion.health import STATUS_SOURCES, ProjectImportEvidence, SourceHealth
from engineering_memory.ingestion.state import ImportStateCorrupt, ImportStateUnavailable
from engineering_memory.memory.interface import MemoryStoreRejected, MemoryStoreUnavailable
from engineering_memory.memory.interface.project_models import (
    ModelKind,
    ProjectModelKey,
    ProjectModelMetadata,
    ProjectModelMetadataReader,
)


class ExplorerStatus:
    def __init__(
        self,
        read_health: Callable[
            [str | None], tuple[list[SourceHealth], ProjectImportEvidence | None]
        ],
        models: ProjectModelMetadataReader,
        *,
        comparable_clocks: bool = True,
    ) -> None:
        self._read_health = read_health
        self._models = models
        self._comparable_clocks = comparable_clocks

    def read(self, project: str | None = None) -> dict:
        try:
            observations, evidence = self._read_health(project)
            recorded = {row.source: row for row in observations}
            sources = [
                recorded.get(source, SourceHealth(source=source)).model_dump(mode="json")
                for source in STATUS_SOURCES
            ]
            available = True
        except (ImportStateCorrupt, ImportStateUnavailable):
            available, sources, evidence = False, [], None
        return {
            "source_status": "available" if available else "unavailable",
            "sources": sources,
            "models": [
                self._model_status(
                    ProjectModelKey(project=project, kind=kind),
                    evidence if self._comparable_clocks else None,
                    available,
                )
                for kind in ModelKind
            ]
            if project is not None
            else [],
        }

    def _model_status(
        self, key: ProjectModelKey, evidence: ProjectImportEvidence | None, state_available: bool
    ) -> dict:
        try:
            metadata = self._models.get_project_model_metadata(key)
        except (MemoryStoreRejected, MemoryStoreUnavailable):
            metadata = ProjectModelMetadata(refresh_state="unavailable")
        refreshed_at = metadata.last_refreshed_at
        freshness = "unknown"
        if refreshed_at is not None:
            if metadata.stale is True or (evidence and evidence.started_at > refreshed_at):
                freshness = "stale"
            elif (
                metadata.stale is False
                and state_available
                and (evidence is None or evidence.completed_at < refreshed_at)
            ):
                freshness = "current"
        return {
            "kind": key.kind.value,
            **metadata.model_dump(mode="json", exclude={"stale"}),
            "freshness": freshness,
        }
