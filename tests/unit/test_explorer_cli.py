"""Exercise local launcher wiring and safe CLI failures."""

from unittest.mock import Mock

from typer.testing import CliRunner

from engineering_memory.cli import app, runtime


def test_launch_publishes_new_credential_and_closes_resources(monkeypatch):
    import uvicorn

    endpoints = []
    closed = []

    def make_access(resources, *, include_neighborhood=False):
        assert include_neighborhood
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
    def fail(resources, *, include_neighborhood=False):
        assert include_neighborhood
        raise RuntimeError("private diagnostic")

    monkeypatch.setattr(runtime, "make_read_access", fail)
    result = CliRunner().invoke(app, ["explore"])

    assert result.exit_code == 1
    assert "Memory explorer could not start" in result.output
    assert "private diagnostic" not in result.output


def test_rebuild_neighborhood_uses_local_archive_without_memory(monkeypatch, tmp_path):
    from engineering_memory.archive.local import LocalRawArchive

    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(tmp_path / "archive"))
    from engineering_memory.archive.interface import OriginalPayload
    from engineering_memory.normalization import Source
    from tests.unit.test_deep_recall import record

    item = record(Source.CODEX, "one", "See https://github.com/example/demo/pull/1")
    archive = LocalRawArchive(tmp_path / "archive")
    archive.store(item, OriginalPayload(content=b"private original", media_type="text/plain"))
    make_memory = Mock(side_effect=AssertionError("memory must remain disconnected"))
    monkeypatch.setattr(runtime, "make_memory", make_memory)

    result = CliRunner().invoke(app, ["rebuild-neighborhood", "--json"])

    assert result.exit_code == 0, result.output
    assert '"indexed": 1' in result.output
    assert "private original" not in result.output
    assert list((tmp_path / "archive").glob("*neighborhood*.sqlite3"))
    make_memory.assert_not_called()
