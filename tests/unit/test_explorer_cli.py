"""Exercise local launcher wiring and safe CLI failures."""

from unittest.mock import Mock

from typer.testing import CliRunner

from engineering_memory.cli import app, runtime


def test_launch_publishes_new_credential_and_closes_resources(monkeypatch):
    import uvicorn

    endpoints = []
    closed = []

    def make_access(resources):
        marker = object()
        resources.callback(closed.append, marker)
        return marker

    status = Mock()

    def serve(server, *, sockets):
        (listener,) = sockets
        assert listener.getsockname()[0] == "127.0.0.1"
        assert listener.getsockname()[1] > 0
        assert server.config.access_log is False
        assert server.config.proxy_headers is False
        endpoints.append(listener)

    monkeypatch.setattr(runtime, "make_read_access", make_access)
    make_status = Mock(return_value=status)
    monkeypatch.setattr(runtime, "make_explorer_status", make_status)
    monkeypatch.setattr(uvicorn.Server, "run", serve)

    launches = [CliRunner().invoke(app, ["explore"]) for _ in range(2)]

    tokens = []
    for launch in launches:
        assert launch.exit_code == 0, launch.output
        url, credential = launch.output.strip().splitlines()
        assert url.startswith("Open http://127.0.0.1:")
        token = credential.removeprefix("Access key: ")
        assert len(token) >= 43
        assert token not in url
        tokens.append(token)
    assert tokens[0] != tokens[1]
    assert len(closed) == 2
    assert make_status.call_count == 2
    assert all(listener.fileno() == -1 for listener in endpoints)


def test_launch_failure_does_not_echo_private_error(monkeypatch):
    def fail(resources):
        raise RuntimeError("private diagnostic")

    monkeypatch.setattr(runtime, "make_read_access", fail)
    result = CliRunner().invoke(app, ["explore"])

    assert result.exit_code == 1
    assert "Memory explorer could not start" in result.output
    assert "private diagnostic" not in result.output
