from typer.testing import CliRunner

from engineering_memory.cli import app
from engineering_memory.memory.hindsight.provision import ProvisionError


def test_provision_success(monkeypatch):
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_LLM__BASE_URL", "http://proxy")
    seen = []
    monkeypatch.setattr(
        "engineering_memory.memory.hindsight.provision.provision",
        lambda settings: seen.append(settings.bank_id),
    )
    result = CliRunner().invoke(app, ["provision"])
    assert result.exit_code == 0, result.output
    assert seen == ["engineering-global"]
    assert "verified" in result.output


def test_provision_failure(monkeypatch):
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_LLM__BASE_URL", "http://proxy")

    def fail(settings):
        raise ProvisionError("provisioning unavailable")

    monkeypatch.setattr("engineering_memory.memory.hindsight.provision.provision", fail)
    result = CliRunner().invoke(app, ["provision"])
    assert result.exit_code == 1
    assert "unavailable" in result.output


def test_provision_settings_failure_is_safe(monkeypatch):
    from engineering_memory.settings import SettingsError

    def fail():
        raise SettingsError("configuration invalid")

    monkeypatch.setattr("engineering_memory.settings.load_settings", fail)
    result = CliRunner().invoke(app, ["provision"])
    assert result.exit_code == 1
    assert "configuration invalid" in result.output


def test_non_ascii_cli_token_is_safe(monkeypatch):
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_LLM__BASE_URL", "http://proxy")
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__TOKEN", "synthetic-canary-☃")
    result = CliRunner().invoke(app, ["provision"])
    assert result.exit_code == 1
    assert "unavailable" in result.output
    assert "synthetic-canary" not in result.output
