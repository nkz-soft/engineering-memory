import os

import pytest
from dotenv import dotenv_values

from engineering_memory import setup_profile
from engineering_memory.settings import workstation_compose_values


def test_profile_writes_matching_endpoints_and_keeps_secret_on_retry(tmp_path, monkeypatch):
    profile, data = tmp_path / "config", tmp_path / "data"
    answers = iter(
        [
            "openai/gpt-4o-mini",
            "test-${VARIABLE}#'key\\\\trail",
            "",
            "9888",
            "5000",
            str(data / "archive"),
            str(data / "import-state.db"),
            "keep",
            "keep",
            "",
        ]
    )
    monkeypatch.setattr(setup_profile.typer, "prompt", lambda *a, **kw: next(answers))
    monkeypatch.setattr(setup_profile.typer, "confirm", lambda *a, **kw: True)
    assert setup_profile.configure(profile, data)
    compose = profile / "compose.env"
    app = profile / "app.env"
    configured = workstation_compose_values(compose)
    assert configured["PRODUCT_PROVIDER_API_KEY"] == "test-${VARIABLE}#'key\\\\trail"
    assert (
        configured["WORKSTATION_PROXY_KEY"] == dotenv_values(app)["ENGINEERING_MEMORY_LLM__API_KEY"]
    )
    assert dotenv_values(app)["ENGINEERING_MEMORY_LLM__BASE_URL"] == "http://127.0.0.1:5000/v1"
    if os.name != "nt":
        assert app.stat().st_mode & 0o777 == 0o600
    with compose.open("a", encoding="utf-8") as stream:
        stream.write("# local comment\nCUSTOM=keep\n")
    monkeypatch.setattr(setup_profile.typer, "prompt", lambda *a, **kw: kw.get("default", ""))
    assert setup_profile.configure(profile, data)
    assert (
        workstation_compose_values(compose)["PRODUCT_PROVIDER_API_KEY"]
        == "test-${VARIABLE}#'key\\\\trail"
    )
    assert "# local comment\nCUSTOM=keep\n" in compose.read_text(encoding="utf-8")


def test_profile_recovers_when_second_replacement_fails(tmp_path, monkeypatch):
    profile, data = tmp_path / "config", tmp_path / "data"
    profile.mkdir()
    app = profile / "app.env"
    compose = profile / "compose.env"
    app.write_text("CUSTOM=old\n", encoding="utf-8")
    compose.write_text(
        "PRODUCT_PROVIDER_MODEL=openai/test\nPRODUCT_PROVIDER_API_KEY=local\n", encoding="utf-8"
    )
    original = (app.read_bytes(), compose.read_bytes())
    monkeypatch.setattr(setup_profile.typer, "prompt", lambda *a, **kw: kw.get("default", ""))
    monkeypatch.setattr(setup_profile.typer, "confirm", lambda *a, **kw: True)
    replace = setup_profile._atomic_write
    replaced = False

    def fail_once(path, contents):
        nonlocal replaced
        if path == app and not replaced:
            replaced = True
            raise OSError("synthetic failure")
        replace(path, contents)

    monkeypatch.setattr(setup_profile, "_atomic_write", fail_once)
    with pytest.raises(setup_profile.ProfileError, match="profile"):
        setup_profile.configure(profile, data)
    assert (app.read_bytes(), compose.read_bytes()) == original


def test_installer_profile_read_defaults_without_writing(tmp_path):
    profile, data = tmp_path / "config", tmp_path / "data"
    fields, has_key, token = setup_profile.read_installer_profile(profile, data)
    assert fields == {
        "provider": "openrouter",
        "model": "openai/gpt-oss-20b",
        "api_base": "https://openrouter.ai/api/v1",
        "backend_port": "8888",
        "litellm_port": "4000",
        "archive": str(data / "archive"),
        "sqlite": str(data / "import-state.db"),
    }
    assert not has_key
    assert token
    assert not profile.exists()


def test_installer_profile_preserves_hidden_assignments_and_existing_model(tmp_path):
    profile, data = tmp_path / "config", tmp_path / "data"
    profile.mkdir()
    compose = profile / "compose.env"
    hidden = (
        'PRODUCT_PROVIDER_API_KEY="literal$$key"\n'
        'WORKSTATION_HTTPS_PROXY="http://user:pass@proxy.invalid:3128"\n'
        'WORKSTATION_PROXY_KEY="local"\n'
        "CUSTOM=preserved\n"
    )
    compose.write_text(
        "PRODUCT_PROVIDER_MODEL=custom_openai/org/model\n" + hidden, encoding="utf-8"
    )
    fields, has_key, token = setup_profile.read_installer_profile(profile, data)
    assert has_key
    assert "literal" not in str((fields, token))
    assert fields["provider"] == "custom_openai"
    assert fields["model"] == "org/model"
    assert fields["api_base"] == ""
    fields["litellm_port"] = "5000"
    setup_profile.apply_installer_profile(profile, data, fields, token, "")
    assert hidden in compose.read_text(encoding="utf-8")
    assert (
        workstation_compose_values(compose)["PRODUCT_PROVIDER_MODEL"] == "custom_openai/org/model"
    )
    assert dotenv_values(profile / "app.env")["ENGINEERING_MEMORY_LLM__BASE_URL"] == (
        "http://127.0.0.1:5000/v1"
    )
    with pytest.raises(setup_profile.InstallerProfileError, match="stale"):
        setup_profile.apply_installer_profile(profile, data, fields, token, "")


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"litellm_port": "08888"}, "litellm_port"),
        ({"backend_port": "65536"}, "backend_port"),
        ({"api_base": "https://user:pass@example.invalid"}, "api_base"),
        ({"sqlite": "relative.db"}, "sqlite"),
        ({"provider": "bad/provider"}, "provider"),
    ],
)
def test_installer_profile_invalid_fields_are_safe(tmp_path, changes, error):
    profile, data = tmp_path / "config", tmp_path / "data"
    fields, _, token = setup_profile.read_installer_profile(profile, data)
    with pytest.raises(setup_profile.InstallerProfileError, match=error):
        setup_profile.apply_installer_profile(profile, data, fields | changes, token, "test-key")
    assert not (profile / "compose.env").exists()
    assert not (profile / "app.env").exists()


def test_installer_profile_requires_key_on_provider_change(tmp_path):
    profile, data = tmp_path / "config", tmp_path / "data"
    fields, _, token = setup_profile.read_installer_profile(profile, data)
    setup_profile.apply_installer_profile(profile, data, fields, token, "test-${KEY}#'é")
    fields, has_key, token = setup_profile.read_installer_profile(profile, data)
    assert has_key
    compose = profile / "compose.env"
    saved = compose.read_bytes()
    assert workstation_compose_values(compose)["PRODUCT_PROVIDER_MODEL"] == (
        "openrouter/openai/gpt-oss-20b"
    )
    assert workstation_compose_values(compose)["PRODUCT_PROVIDER_API_KEY"] == "test-${KEY}#'é"
    with pytest.raises(setup_profile.InstallerProfileError, match="api_key"):
        setup_profile.apply_installer_profile(
            profile, data, fields | {"provider": "openai"}, token, ""
        )
    assert compose.read_bytes() == saved


@pytest.mark.skipif(os.name != "nt", reason="Windows path syntax")
@pytest.mark.parametrize("name", ["unsafe*.db", "state.db:alternate", "NUL"])
def test_installer_rejects_names_windows_cannot_use_for_sqlite(tmp_path, name):
    profile, data = tmp_path / "config", tmp_path / "data"
    fields, _, token = setup_profile.read_installer_profile(profile, data)
    with pytest.raises(setup_profile.InstallerProfileError, match="sqlite"):
        setup_profile.apply_installer_profile(
            profile, data, fields | {"sqlite": str(data / name)}, token, "test-key"
        )
    assert not (profile / "compose.env").exists()
