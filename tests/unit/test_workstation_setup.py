import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from engineering_memory.cli import app

runner = CliRunner()


def test_setup_requires_terminal_before_touching_profile():
    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 1
    assert "interactive terminal" in result.output
    assert "No such command" not in result.output


@pytest.mark.parametrize("failure", [None, "start", "provision", "clients"])
def test_setup_orders_workstation_stages(monkeypatch, tmp_path, failure):
    from engineering_memory.cli import setup
    from engineering_memory.cli.stack import StackError

    events = []
    profile = tmp_path / "config"
    data = tmp_path / "data"
    executable = tmp_path / "Engineering Memory" / "engineering-memory"
    monkeypatch.setattr(setup, "has_terminal", lambda: True)
    monkeypatch.setattr(setup.workstation, "is_installed", lambda: True)
    monkeypatch.setattr(setup.workstation, "locations", lambda: (profile, data))
    monkeypatch.setattr(sys, "executable", str(executable))

    def save(selected_profile: Path, selected_data: Path) -> bool:
        assert (selected_profile, selected_data) == (profile, data)
        events.append("profile")
        return True

    def stack(action: str) -> None:
        events.append(action)
        if failure == action:
            raise StackError("Backend startup failed. Check port availability.")

    def provision(data):
        events.append("provision")
        if failure == "provision":
            raise RuntimeError("synthetic-secret-marker")

    def clients(installed_executable: Path) -> bool:
        assert installed_executable == executable
        events.append("clients")
        return failure != "clients"

    def history() -> bool:
        events.append("import")
        return True

    monkeypatch.setattr(setup.setup_profile, "configure", save)
    monkeypatch.setattr(setup, "run_stack", stack)
    monkeypatch.setattr(setup.cli, "run_provision", provision)
    monkeypatch.setattr(setup.setup_clients, "configure", clients)
    monkeypatch.setattr(setup.setup_history, "import_selected", history)

    result = runner.invoke(app, ["setup"], input="y\n")
    expected = ["profile", "check", "start"]
    if failure != "start":
        expected.append("provision")
    if failure not in {"start", "provision"}:
        expected.extend(["clients", "import"])
    assert events == expected
    assert result.exit_code == (1 if failure else 0)
    assert "synthetic-secret-marker" not in result.output
    if failure in {"start", "provision"}:
        assert "History import deferred" in result.output


def test_setup_rejects_ambient_backend_override(monkeypatch):
    from engineering_memory.cli import setup

    monkeypatch.setattr(setup, "has_terminal", lambda: True)
    monkeypatch.setattr(setup.workstation, "is_installed", lambda: True)
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://example.invalid:1234")

    def unexpected(*args):
        pytest.fail("Setup must stop before it changes a profile or starts the backend")

    monkeypatch.setattr(setup.setup_profile, "configure", unexpected)
    result = runner.invoke(app, ["setup"])
    assert result.exit_code == 1
    assert "ENGINEERING_MEMORY_HINDSIGHT__BASE_URL" in result.output
    assert "example.invalid" not in result.output
