from subprocess import CompletedProcess

import httpx
import pytest
import typer
from typer.testing import CliRunner

from engineering_memory import setup_profile
from engineering_memory.cli import setup, stack


def test_setup_saves_keeps_replaces_and_clears_private_proxy(tmp_path):
    profile = tmp_path / "profile"
    data = tmp_path / "data"
    app = typer.Typer()

    @app.command()
    def configure():
        setup_profile.configure(profile, data)

    def run(values):
        result = CliRunner().invoke(app, input="\n".join(values) + "\n")
        assert result.exit_code == 0, result.output
        assert "synthetic%40password" not in result.output

    initial = "http://user:synthetic%40password@proxy.example:3128"
    replacement = "https://replacement.example:8443"
    compose = profile / "compose.env"
    run(["openai/test", "provider-test", "", "", "", "", "", "", "", "", "y"])
    # Existing non-proxy prompts retain their defaults on each rerun.
    defaults = [""] * 7
    run([*defaults, "set", initial, "", "internal.example", "y"])
    assert initial in compose.read_text(encoding="utf-8")
    run([*defaults, "", "", "", "y"])
    assert initial in compose.read_text(encoding="utf-8")
    run([*defaults, "set", replacement, "", "", "n"])
    assert initial in compose.read_text(encoding="utf-8")
    run([*defaults, "set", replacement, "", "", "y"])
    assert replacement in compose.read_text(encoding="utf-8")
    run([*defaults, "clear", "", "-", "y"])
    saved = compose.read_text(encoding="utf-8")
    assert initial not in saved and replacement not in saved
    assert "internal.example" not in saved


@pytest.mark.parametrize("managed", [False, True])
def test_compose_selects_proxy_overlay_only_for_managed_profile(monkeypatch, tmp_path, managed):
    profile = tmp_path / "compose.env"
    profile.write_text(
        "WORKSTATION_HTTPS_PROXY=http://proxy.example:3128\n" if managed else "",
        encoding="utf-8",
    )
    monkeypatch.setattr(stack.workstation, "locations", lambda: (tmp_path, tmp_path))
    monkeypatch.setattr(stack, "deployment_file", lambda: tmp_path / "compose.yaml")
    monkeypatch.setattr(stack.shutil, "which", lambda _: "docker")
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        output = "linux 28.0.0" if "info" in args else "2.24.4"
        return CompletedProcess(args, 0, output)

    monkeypatch.setattr(stack.subprocess, "run", run)
    stack.run_stack("start")
    for args in calls[-2:]:
        assert (str(tmp_path / "compose.proxy.yaml") in args) is managed
        assert all("proxy.example" not in value for value in args)


@pytest.mark.parametrize("status", [200, 204, 407, 502, None, "malformed", "oversize"])
def test_route_probe_uses_only_loopback_and_hides_provider_errors(monkeypatch, tmp_path, status):
    (tmp_path / "compose.env").write_text(
        "WORKSTATION_PROXY_PORT=4400\nWORKSTATION_PROXY_KEY=synthetic-local-key\n"
        "WORKSTATION_HTTPS_PROXY=http://synthetic:secret@proxy.example:3128\n",
        encoding="utf-8",
    )

    def respond(request):
        assert str(request.url) == "http://127.0.0.1:4400/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer synthetic-local-key"
        assert b"engineering-extraction" in request.content
        if status is None:
            raise httpx.ReadTimeout("synthetic:secret")
        if status == 200:
            return httpx.Response(status, json={"choices": [{"message": {"content": "OK"}}]})
        if status == "malformed":
            return httpx.Response(200, content=b"synthetic:secret")
        if status == "oversize":
            return httpx.Response(200, content=b" " * 65536 + b'{"choices": [{}]}')
        return httpx.Response(status, content=b"synthetic:secret")

    monkeypatch.setattr(setup.typer, "confirm", lambda *args, **kwargs: True)
    client = httpx.Client
    monkeypatch.setattr(
        setup.httpx,
        "Client",
        lambda **options: client(transport=httpx.MockTransport(respond), **options),
    )
    if status == 200:
        setup._check_provider_route(tmp_path)
    else:
        with pytest.raises(stack.StackError, match="proxy") as caught:
            setup._check_provider_route(tmp_path)
        assert "synthetic:secret" not in str(caught.value)


@pytest.mark.parametrize("value", ["example.com:abc", "::g", "example.com,,localhost", "*"])
def test_rejects_bypass_entries_that_are_not_hosts(value):
    assert not setup_profile._valid_bypass(value)
