from datetime import UTC, datetime, timedelta

from engineering_memory.ingestion.state import ImportStateUnavailable
from engineering_memory.memory.interface import MemoryStoreUnavailable
from engineering_memory.normalization import Source

NOW = datetime(2026, 11, 19, tzinfo=UTC)


def test_status_is_project_scoped_and_keeps_available_rows():
    from engineering_memory.access.status import ExplorerStatus
    from engineering_memory.ingestion.health import ProjectImportEvidence, SourceHealth
    from engineering_memory.memory.interface.project_models import ProjectModelMetadata

    def read_health(project):
        return [
            SourceHealth(
                source=Source.CODEX,
                outcome="failed",
                last_attempt_at=NOW,
                error_categories=("PRIVATE_SOURCE_ERROR",),
            ),
        ], (
            ProjectImportEvidence(started_at=NOW, completed_at=NOW)
            if project == "orchard"
            else None
        )

    class Models:
        def get_project_model_metadata(self, key):
            if key.kind == "decisions":
                raise MemoryStoreUnavailable("PRIVATE_MODEL_ERROR")
            return ProjectModelMetadata(
                refresh_state="ready",
                last_refreshed_at=NOW - timedelta(hours=1),
                last_refresh_failed_at=NOW,
                stale=None if key.kind == "stack" else False,
            )

    status = ExplorerStatus(read_health, Models())
    partial = status.read("orchard")
    assert [model["freshness"] for model in partial["models"]] == ["stale", "stale", "unknown"]
    assert partial["models"][0]["last_refresh_failed_at"] == "2026-11-19T00:00:00Z"
    assert partial["models"][2]["refresh_state"] == "unavailable"
    assert len(partial["sources"]) == 4
    assert partial["sources"][-1]["error_categories"] == ["unknown"]
    assert "PRIVATE_" not in str(partial)
    other = status.read("other")
    assert [model["freshness"] for model in other["models"]] == ["current", "unknown", "unknown"]
    assert status.read()["models"] == []


def test_unreadable_source_state_cannot_prove_current():
    from engineering_memory.access.status import ExplorerStatus
    from engineering_memory.memory.interface.project_models import ProjectModelMetadata

    def broken(project):
        raise ImportStateUnavailable("PRIVATE_PATH")

    class Models:
        def get_project_model_metadata(self, key):
            return ProjectModelMetadata(
                refresh_state="ready",
                last_refreshed_at=NOW,
                stale=key.kind == "stack",
            )

    status = ExplorerStatus(broken, Models()).read("orchard")
    assert status["source_status"] == "unavailable"
    assert status["sources"] == []
    assert [model["freshness"] for model in status["models"]] == ["unknown", "stale", "unknown"]
    assert "PRIVATE_PATH" not in str(status)


def test_overlap_and_remote_clocks_do_not_establish_staleness():
    from engineering_memory.access.status import ExplorerStatus
    from engineering_memory.ingestion.health import ProjectImportEvidence
    from engineering_memory.memory.interface.project_models import ProjectModelMetadata

    started_at = NOW - timedelta(minutes=1)
    evidence = ProjectImportEvidence(started_at=started_at, completed_at=NOW)

    class Models:
        def get_project_model_metadata(self, key):
            return ProjectModelMetadata(
                refresh_state="ready",
                stale=False,
                last_refreshed_at=(
                    started_at - timedelta(seconds=1) if key.kind == "architecture" else started_at
                ),
            )

    def read_health(project):
        return [], evidence

    local = ExplorerStatus(read_health, Models())
    assert [row["freshness"] for row in local.read("orchard")["models"]] == [
        "stale",
        "unknown",
        "unknown",
    ]
    remote = ExplorerStatus(read_health, Models(), comparable_clocks=False)
    assert {row["freshness"] for row in remote.read("orchard")["models"]} == {"current"}
