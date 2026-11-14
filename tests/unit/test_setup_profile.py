import os

import pytest
from dotenv import dotenv_values

from engineering_memory import setup_profile


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
        ]
    )
    monkeypatch.setattr(setup_profile.typer, "prompt", lambda *a, **kw: next(answers))
    monkeypatch.setattr(setup_profile.typer, "confirm", lambda *a, **kw: True)
    assert setup_profile.configure(profile, data)
    compose = profile / "compose.env"
    app = profile / "app.env"
    configured = setup_profile._compose_values(compose)
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
        setup_profile._compose_values(compose)["PRODUCT_PROVIDER_API_KEY"]
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
