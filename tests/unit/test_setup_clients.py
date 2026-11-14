import json
from pathlib import Path

from engineering_memory import setup_clients


def test_codex_registration_uses_active_profile_and_absolute_argv(tmp_path, monkeypatch):
    profile = tmp_path / "custom profile"
    cli = tmp_path / ("codex.exe" if setup_clients.os.name == "nt" else "codex")
    executable = tmp_path / "Engineering Memory" / "engineering-memory.exe"
    monkeypatch.setenv("CODEX_HOME", str(profile))
    monkeypatch.setattr(
        setup_clients.shutil,
        "which",
        lambda name, **kwargs: str(cli) if Path(name).name == "codex" else None,
    )
    calls = []

    def run(target, *args):
        assert target.profile.is_dir()
        calls.append((target.profile, args))
        if args == ("mcp", "list", "--json"):
            return 0, "[]"
        return 0, ""

    monkeypatch.setattr(setup_clients, "_run", run)
    monkeypatch.setattr(setup_clients.typer, "confirm", lambda *a, **kw: True)
    assert setup_clients.configure(executable)
    assert calls == [
        (profile, ("mcp", "list", "--json")),
        (profile, ("mcp", "add", "engineering-memory", "--", str(executable), "serve")),
    ]


def test_codex_identical_registration_does_not_write(tmp_path, monkeypatch):
    target = setup_clients.Client("Codex", Path("codex"), tmp_path)
    executable = tmp_path / "engineering-memory"
    monkeypatch.setattr(setup_clients, "discover", lambda: [target])

    def run(target, *args):
        assert target.profile.is_dir()
        assert args == ("mcp", "list", "--json")
        return 0, json.dumps(
            [
                {
                    "name": "engineering-memory",
                    "transport": {"command": str(executable), "args": ["serve"]},
                    "enabled": True,
                }
            ]
        )

    monkeypatch.setattr(setup_clients, "_run", run)
    monkeypatch.setattr(setup_clients.typer, "confirm", lambda *a, **kw: True)
    assert setup_clients.configure(executable)


def test_client_search_ignores_implicit_working_directory(tmp_path, monkeypatch):
    work = tmp_path / "checkout"
    work.mkdir()
    monkeypatch.chdir(work)
    name = "codex.exe" if setup_clients.os.name == "nt" else "codex"
    impersonator = work / name
    impersonator.touch(mode=0o700)
    monkeypatch.setenv("PATH", ".")
    assert setup_clients._find_cli("codex") is None
