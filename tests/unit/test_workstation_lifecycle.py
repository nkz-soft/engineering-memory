from subprocess import CompletedProcess

import pytest

from engineering_memory import workstation
from engineering_memory.cli import stack


@pytest.fixture
def profile(monkeypatch, tmp_path):
    (tmp_path / "compose.env").write_text("WORKSTATION_PROXY_KEY=example\n", encoding="utf-8")
    monkeypatch.setattr(workstation, "locations", lambda: (tmp_path, tmp_path))
    monkeypatch.setattr(stack, "deployment_file", lambda: tmp_path / "assets" / "compose.yaml")
    monkeypatch.setattr(stack.shutil, "which", lambda _: "docker")
    return tmp_path


def test_stop_preserves_volumes_and_uses_explicit_paths(monkeypatch, profile):
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        return CompletedProcess(args, 0, "linux 28.0.0" if "info" in args else "2.24.4")

    monkeypatch.setattr(stack.subprocess, "run", run)
    stack.run_stack("stop")
    assert calls[-1][-1:] == ["stop"]
    assert "--volumes" not in calls[-1]
    assert str(profile / "compose.env") in calls[-1]
    assert str(profile / "assets" / "compose.yaml") in calls[-1]
    assert "engineering-memory-workstation" in calls[-1]


@pytest.mark.parametrize(
    ("version", "daemon_code", "message"),
    [("2.23.0", 0, "2.24.4"), ("2.24.4", 1, "daemon")],
)
def test_check_reports_prerequisites(monkeypatch, profile, version, daemon_code, message):
    def run(args, **kwargs):
        return CompletedProcess(
            args,
            daemon_code if "info" in args else 0,
            "linux 28.0.0" if "info" in args else version,
        )

    monkeypatch.setattr(stack.subprocess, "run", run)
    with pytest.raises(stack.StackError, match=message):
        stack.run_stack("check")


def test_start_error_does_not_relay_compose_output(monkeypatch, profile):
    def run(args, **kwargs):
        if "up" in args:
            return CompletedProcess(args, 1, "bind: address already in use secret-value")
        return CompletedProcess(args, 0, "linux 28.0.0" if "info" in args else "2.24.4")

    monkeypatch.setattr(stack.subprocess, "run", run)
    with pytest.raises(stack.StackError, match="port") as caught:
        stack.run_stack("start")
    assert "secret-value" not in str(caught.value)


def test_missing_docker_has_actionable_error(monkeypatch):
    monkeypatch.setattr(stack.shutil, "which", lambda _: None)
    with pytest.raises(stack.StackError, match="Install Docker"):
        stack.run_stack("check")


def test_check_rejects_windows_container_mode(monkeypatch, profile):
    def run(args, **kwargs):
        return CompletedProcess(args, 0, "windows" if "info" in args else "2.24.4")

    monkeypatch.setattr(stack.subprocess, "run", run)
    with pytest.raises(stack.StackError, match="Linux containers"):
        stack.run_stack("check")


def test_check_rejects_engine_with_unsafe_loopback_publishing(monkeypatch, profile):
    def run(args, **kwargs):
        return CompletedProcess(args, 0, "linux 27.5.1" if "info" in args else "2.24.4")

    monkeypatch.setattr(stack.subprocess, "run", run)
    with pytest.raises(stack.StackError, match="Docker Engine 28"):
        stack.run_stack("check")
