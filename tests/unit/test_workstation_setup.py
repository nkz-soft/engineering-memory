import os
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


@pytest.mark.parametrize("failure", [None, "docker", "start", "provision", "clients"])
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

    def check_docker() -> str:
        events.append("docker")
        if failure == "docker":
            raise StackError("Start Docker and check permissions to access the daemon.")
        return "docker"

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

    monkeypatch.setattr(setup, "check_docker", check_docker)
    monkeypatch.setattr(setup.setup_profile, "configure", save)
    monkeypatch.setattr(setup, "run_stack", stack)
    monkeypatch.setattr(setup.cli, "run_provision", provision)
    monkeypatch.setattr(setup.setup_clients, "configure", clients)
    monkeypatch.setattr(setup.setup_history, "import_selected", history)

    result = runner.invoke(app, ["setup"], input="y\n")
    expected = ["docker"]
    if failure != "docker":
        expected.extend(["profile", "check", "start"])
        if failure != "start":
            expected.append("provision")
    expected.append("clients")
    if failure not in {"docker", "start", "provision"}:
        expected.append("import")
    assert events == expected
    assert result.exit_code == (1 if failure else 0)
    assert "synthetic-secret-marker" not in result.output
    if failure in {"docker", "start", "provision"}:
        assert "History import deferred" in result.output
        assert "Backend ready and bank provisioned" not in result.output
    if failure == "docker":
        assert "Start Docker" in result.output
        assert "Start the local backend" not in result.output


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


def installer_home(monkeypatch, tmp_path):
    from engineering_memory.cli import setup

    profile, data = tmp_path / "config", tmp_path / "Данные 🚀"
    monkeypatch.setattr(setup, "_supported_installer_user", lambda: True, raising=False)
    monkeypatch.setattr(setup.workstation, "locations", lambda: (profile, data))
    return setup, profile, data


def test_installer_read_and_save_keep_key_private(monkeypatch, tmp_path):
    setup, profile, data = installer_home(monkeypatch, tmp_path)
    read = runner.invoke(app, ["setup", "--installer-ui", "read"])
    assert read.exit_code == 0, read.output
    lines = read.stdout.splitlines()
    assert lines[:2] == ["EM1", "0"]
    fields = [bytes.fromhex(line[1:]).decode("utf-8") for line in lines[3:]]
    assert fields[:3] == ["openrouter", "openai/gpt-oss-20b", "https://openrouter.ai/api/v1"]
    assert str(data / "archive") in fields
    assert not profile.exists()

    monkeypatch.setenv("EM_INSTALLER_UI_VERSION", "EM1")
    monkeypatch.setenv("EM_INSTALLER_UI_TOKEN", lines[2])
    for field, value in zip(setup.setup_profile.INSTALLER_FIELDS, fields, strict=True):
        monkeypatch.setenv("EM_INSTALLER_UI_" + field.upper(), "v" + value)
    monkeypatch.setenv("EM_INSTALLER_UI_API_KEY", "vSYNTHETIC-install-key")
    assert runner.invoke(app, ["setup", "--installer-ui", "save"]).stdout == "saved\n"
    assert "EM_INSTALLER_UI_API_KEY" not in os.environ
    reopened = runner.invoke(app, ["setup", "--installer-ui", "read"])
    assert reopened.stdout.splitlines()[:2] == ["EM1", "1"]
    assert "SYNTHETIC-install-key" not in reopened.output
    assert "EM_INSTALLER_UI_" not in "\n".join(os.environ)


def test_installer_malformed_request_clears_environment(monkeypatch, tmp_path):
    _, profile, _ = installer_home(monkeypatch, tmp_path)
    monkeypatch.setenv("EM_INSTALLER_UI_VERSION", "invalid")
    monkeypatch.setenv("EM_INSTALLER_UI_API_KEY", "vSYNTHETIC-install-key")
    invalid = runner.invoke(app, ["setup", "--installer-ui", "save"])
    assert invalid.exit_code == 1
    assert invalid.stdout == "request\n"
    assert "SYNTHETIC" not in invalid.output
    assert "EM_INSTALLER_UI_API_KEY" not in os.environ
    assert not profile.exists()


@pytest.mark.parametrize(
    ("failure", "status", "events"),
    [
        ("check", "prerequisite", ["check"]),
        ("start", "startup", ["check", "start"]),
        ("provision", "bank", ["check", "start", "provision"]),
        (None, "ready", ["check", "start", "provision"]),
    ],
)
def test_installer_reports_safe_backend_stage(monkeypatch, tmp_path, failure, status, events):
    setup, _, _ = installer_home(monkeypatch, tmp_path)
    from engineering_memory.cli.stack import StackError

    calls = []
    monkeypatch.setenv("EM_INSTALLER_UI_API_KEY", "vSYNTHETIC-install-key")

    def stack(action):
        assert not os.environ.get("EM_INSTALLER_UI_API_KEY")
        calls.append(action)
        if action == failure:
            raise StackError("SYNTHETIC-install-key")

    def provision(_):
        calls.append("provision")
        if failure == "provision":
            raise RuntimeError("SYNTHETIC-install-key")

    monkeypatch.setattr(setup, "run_stack", stack)
    monkeypatch.setattr(setup.cli, "run_provision", provision)
    result = runner.invoke(app, ["setup", "--installer-ui", "start"])
    assert result.stdout == status + "\n"
    assert result.exit_code == bool(failure)
    assert calls == events
    assert "SYNTHETIC" not in result.output


def test_installer_client_actions_require_snapshot_and_keep_profile_private(monkeypatch, tmp_path):
    from engineering_memory import setup_mcp_probe
    from engineering_memory.cli import setup
    from engineering_memory.setup_client_discovery import Client

    path = tmp_path / "Profil Codex é" / "config.toml"
    path.parent.mkdir()
    path.write_text('service_tier = "default"\nmodel = "fixture-secret-value"\n', encoding="utf-8")
    clients = (
        Client("codex-cli", "Codex CLI", path),
        Client("codex-desktop", "Codex Desktop", path),
    )
    monkeypatch.setattr(setup, "_supported_installer_user", lambda: True)
    monkeypatch.setattr(setup.setup_clients, "discover", lambda: clients)
    monkeypatch.setattr(setup_mcp_probe, "probe", lambda executable: "passed")
    preview = setup._installer_output("mcp-scan", {})
    assert preview[0] == "EM-MCP1"
    assert len(preview) == 6
    _, token, status, names, config, warning = preview

    def decode(field):
        return bytes.fromhex(field[1:]).decode()

    assert status == "absent"
    assert decode(names) == "Codex CLI, Codex Desktop"
    assert Path(decode(config)) == path
    assert "service_tier" in decode(warning)
    assert "fixture-secret-value" not in decode(warning)
    before = path.read_bytes()
    assert setup._installer_output("mcp-apply", {"mcp": f"{token}:keep"})[0] == "EM-MCP1"
    assert path.read_bytes() != before
    assert setup._installer_output("mcp-apply", {"mcp": f"{token}:replace"})[1] == "blocked"
    assert "fixture-secret-value" in path.read_text(encoding="utf-8")


def test_terminal_client_setup_available_when_backend_deferred(monkeypatch, tmp_path):
    from engineering_memory.cli import setup

    events = []
    monkeypatch.setattr(setup, "has_terminal", lambda: True)
    monkeypatch.setattr(setup.workstation, "is_installed", lambda: True)
    monkeypatch.setattr(setup.workstation, "locations", lambda: (tmp_path, tmp_path))
    monkeypatch.setattr(setup.os, "geteuid", lambda: 1000, raising=False)
    monkeypatch.setattr(setup, "check_docker", lambda: None)
    monkeypatch.setattr(setup.setup_profile, "configure", lambda *args: True)
    monkeypatch.setattr(setup, "run_stack", lambda action: events.append(action))
    monkeypatch.setattr(setup.setup_clients, "configure", lambda _: not events.append("register"))
    monkeypatch.setattr(
        setup.setup_history, "import_selected", lambda: pytest.fail("History is deferred")
    )

    result = runner.invoke(app, ["setup"], input="n\n")
    assert result.exit_code == 0
    assert events == ["check", "register"]
    assert "MCP registration reviewed" in result.output
