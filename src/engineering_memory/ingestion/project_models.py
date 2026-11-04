"""Importer-side maintenance of disposable synthesis over already imported history."""

from engineering_memory.memory.interface import MemoryStoreRejected, MemoryStoreUnavailable
from engineering_memory.memory.interface.project_models import (
    ModelKind,
    ProjectModelKey,
    ProjectModelMaintainer,
    RefreshOutcome,
)


def refresh_project_models(
    maintainer: ProjectModelMaintainer, keys: tuple[ProjectModelKey, ...]
) -> tuple[RefreshOutcome, ...]:
    outcomes = []
    for key in keys:
        try:
            outcome = maintainer.refresh_project_model(key)
            if outcome.key != key:
                raise MemoryStoreRejected("model identity mismatch")
        except MemoryStoreUnavailable:
            outcome = RefreshOutcome(key=key, status="unavailable", error="unavailable")
        except MemoryStoreRejected:
            outcome = RefreshOutcome(key=key, status="failed", error="rejected")
        except Exception:
            outcome = RefreshOutcome(key=key, status="failed", error="internal")
        outcomes.append(outcome)
    return tuple(outcomes)


def model_keys(project: str, kind: str | None) -> tuple[ProjectModelKey, ...]:
    return tuple(
        ProjectModelKey(project=project, kind=value)
        for value in ((kind,) if kind is not None else tuple(ModelKind))
    )
