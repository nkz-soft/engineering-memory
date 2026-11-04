"""Neutral model values reject ambiguous scope and inconsistent readiness."""

import pytest
from pydantic import ValidationError


def test_project_model_key_validates_exact_classified_scope():
    from engineering_memory.memory.interface.project_models import ProjectModelKey

    key = ProjectModelKey(project="alpha", kind="architecture")
    assert key.model_dump(mode="json") == {"project": "alpha", "kind": "architecture"}
    for project in ("", " ", "Alpha", "unknown", "unclassified", "alpha:beta", 42):
        with pytest.raises(ValidationError):
            ProjectModelKey(project=project, kind="stack")
    with pytest.raises(ValidationError):
        ProjectModelKey(project="alpha", kind="anything")


def test_read_result_cannot_claim_ready_without_snapshot():
    from engineering_memory.memory.interface.project_models import ProjectModelKey, ProjectModelRead

    key = ProjectModelKey(project="alpha", kind="stack")
    assert ProjectModelRead(key=key, status="missing").snapshot is None
    with pytest.raises(ValidationError):
        ProjectModelRead(key=key, status="ready")
