from pathlib import Path

import pytest

from engineering_memory import settings, workstation


def test_frozen_loaders_share_private_profile(monkeypatch, tmp_path):
    profile = tmp_path / "profile with spaces"
    profile.mkdir()
    (profile / "app.env").write_text(
        "ENGINEERING_MEMORY_HINDSIGHT__BASE_URL=http://127.0.0.1:8888\n"
        "ENGINEERING_MEMORY_LLM__BASE_URL=http://127.0.0.1:4000/v1\n"
        "ENGINEERING_MEMORY_LLM__API_KEY=example-placeholder\n",
        encoding="utf-8",
    )
    data = tmp_path / "durable data"
    monkeypatch.setattr(workstation.sys, "frozen", True, raising=False)
    monkeypatch.setattr(workstation, "locations", lambda: (profile, data))
    monkeypatch.chdir(tmp_path)

    assert settings.load_settings().archive_root == data / "archive"
    assert settings.load_access_settings().archive_root == data / "archive"
    assert settings.load_state_path() == data / "import-state.db"
    with pytest.raises(settings.SettingsError):
        settings.load_settings(env_file=None)


def test_frozen_environment_can_override_default_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(workstation.sys, "frozen", True, raising=False)
    monkeypatch.setattr(workstation, "locations", lambda: (tmp_path, tmp_path))
    target = Path(tmp_path / "other state.db")
    monkeypatch.setenv("ENGINEERING_MEMORY_IMPORT_STATE_PATH", str(target))

    assert settings.load_state_path() == target


def test_malformed_profile_does_not_echo_pasted_secret(monkeypatch, tmp_path):
    monkeypatch.setattr(workstation.sys, "frozen", True, raising=False)
    monkeypatch.setattr(workstation, "locations", lambda: (tmp_path, tmp_path))
    (tmp_path / "app.env").write_text("example-private-value\n", encoding="utf-8")
    with pytest.raises(settings.SettingsError, match="line 1") as caught:
        settings.load_settings()
    assert "example-private-value" not in str(caught.value)
