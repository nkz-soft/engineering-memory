"""Operator maintenance has independent outcomes and never hides partial failure."""

import json

import pytest
from typer.testing import CliRunner

from engineering_memory.cli import app
from engineering_memory.memory.interface import MemoryStoreUnavailable
from engineering_memory.memory.interface.project_models import RefreshOutcome


class Maintainer:
    def __init__(self):
        self.keys = []
        self.closed = False

    def refresh_project_model(self, key):
        self.keys.append(key)
        if key.kind == "stack":
            raise MemoryStoreUnavailable("PRIVATE_SENTINEL")
        return RefreshOutcome(key=key, status="completed", refreshed_at="2026-11-04T09:00:00Z")

    def close(self):
        self.closed = True


def test_refresh_all_preserves_partial_results(monkeypatch, tmp_path):
    from engineering_memory.cli import runtime

    maintainer = Maintainer()
    monkeypatch.setattr(runtime, "make_project_models", lambda _: maintainer)
    monkeypatch.setattr("engineering_memory.settings.DEFAULT_ENV_FILE", None)
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(tmp_path / "archive"))
    result = CliRunner().invoke(app, ["models", "refresh", "--project", "alpha", "--json"])
    assert result.exit_code == 1, result.output
    data = json.loads(result.stdout)
    assert data["status"] == "partial" and data["project"] == "alpha"
    assert [row["status"] for row in data["models"]] == ["completed", "unavailable", "completed"]
    assert "PRIVATE" not in result.output and maintainer.closed
    assert not (tmp_path / "archive").exists()


@pytest.mark.parametrize(
    "project,kind", [("unknown", "stack"), ("", "stack"), ("alpha", "unsupported")]
)
def test_invalid_cli_model_scope_before_configuration(monkeypatch, project, kind):
    from engineering_memory.cli import runtime

    def refuse(_):
        raise AssertionError("network adapter constructed")

    monkeypatch.setattr(runtime, "make_project_models", refuse)
    result = CliRunner().invoke(
        app, ["models", "refresh", "--project", project, "--kind", kind, "--json"]
    )
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"] == "usage"


def test_selected_kind_success_human_output(monkeypatch, tmp_path):
    from engineering_memory.cli import runtime

    maintainer = Maintainer()
    monkeypatch.setattr(runtime, "make_project_models", lambda _: maintainer)
    monkeypatch.setattr("engineering_memory.settings.DEFAULT_ENV_FILE", None)
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(tmp_path))
    result = CliRunner().invoke(
        app, ["models", "refresh", "--project", "alpha", "--kind", "decisions"]
    )
    assert result.exit_code == 0, result.output
    assert "decisions: completed" in result.output
    assert [key.kind for key in maintainer.keys] == ["decisions"]
