"""Launch/configuration contracts for read-only consumer access."""

from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from engineering_memory.cli import app
from engineering_memory.settings import SettingsError, load_access_settings


@pytest.fixture
def environment(monkeypatch, tmp_path):
    monkeypatch.setattr("engineering_memory.settings.DEFAULT_ENV_FILE", None)
    monkeypatch.delenv("ENGINEERING_MEMORY_LLM__BASE_URL", raising=False)
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(tmp_path / "archive"))
    return tmp_path


def test_access_settings_do_not_require_extraction(environment):
    settings = load_access_settings()
    assert settings.hindsight.bank_id == "engineering-global"
    assert settings.archive_root == environment / "archive"
    assert not (environment / "archive").exists()


def test_access_settings_safe_failure(environment, monkeypatch):
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "PRIVATE")
    with pytest.raises(SettingsError) as raised:
        load_access_settings()
    assert "PRIVATE" not in str(raised.value)
    assert raised.value.__context__ is None


def test_serve_composes_reads_and_closes(environment, monkeypatch):
    memory = Mock()
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", lambda _: memory)
    serve = Mock()
    monkeypatch.setattr("engineering_memory.access.server.run_stdio", serve)
    result = CliRunner().invoke(app, ["serve"])
    assert result.exit_code == 0, result.output
    assert result.stdout == ""
    service = serve.call_args.args[0]
    assert service.memory is memory
    memory.retain.assert_not_called()
    memory.close.assert_called_once()
    assert not (environment / "archive").exists()


def test_serve_failure_only_safe_stderr(environment, monkeypatch):
    def fail(_):
        raise RuntimeError("PRIVATE")

    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", fail)
    result = CliRunner().invoke(app, ["serve"])
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "internal" in result.stderr and "PRIVATE" not in result.output
