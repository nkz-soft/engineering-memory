"""Operator output contract and offline status privacy."""

import json
import sqlite3

import pytest
from typer.testing import CliRunner

from engineering_memory.cli import app
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.ingestion.state import ImportStatus
from tests.contracts.state import record


@pytest.fixture
def local(monkeypatch, tmp_path):
    from engineering_memory import settings

    monkeypatch.setattr(settings, "DEFAULT_ENV_FILE", None)
    monkeypatch.setenv("ENGINEERING_MEMORY_IMPORT_STATE_PATH", str(tmp_path / "state.db"))
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_LLM__BASE_URL", "http://proxy")
    return tmp_path / "state.db"


def test_provision_json(local, monkeypatch):
    monkeypatch.setattr("engineering_memory.memory.hindsight.provision.provision", lambda _: None)
    result = CliRunner().invoke(app, ["provision", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["mission_verified"] is True
    assert data["schema_version"] == 1
    assert data["status"] == "success"


@pytest.mark.parametrize("error", [RuntimeError("SECRET"), KeyboardInterrupt()])
def test_provision_safe_failure(local, monkeypatch, error):
    def fail(_):
        raise error

    monkeypatch.setattr("engineering_memory.memory.hindsight.provision.provision", fail)
    result = CliRunner().invoke(app, ["provision", "--json"])
    assert result.exit_code == (130 if isinstance(error, KeyboardInterrupt) else 1)
    assert json.loads(result.stdout)["status"] == "failure"
    assert "SECRET" not in result.output


def test_status_offline_and_readonly(local, monkeypatch):
    state = SQLiteImportState(local)
    state.initialize()
    state.record(record())
    state.record(record(ImportStatus.FAILED, source_id="bad"))
    state.close()
    before = local.read_bytes()
    monkeypatch.delenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL")
    monkeypatch.delenv("ENGINEERING_MEMORY_LLM__BASE_URL")
    result = CliRunner().invoke(app, ["status", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert (data["imported"], data["failed"]) == (1, 1)
    assert [r["source_id"] for r in data["records"]] == ["abc123", "bad"]
    assert data["records"][1]["error"] == "unknown"
    assert local.read_bytes() == before


def test_missing_status_creates_nothing(local):
    result = CliRunner().invoke(app, ["status", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["records"] == []
    assert not local.exists()


def test_corrupt_status_is_safe(local):
    local.write_bytes(b"SECRET")
    result = CliRunner().invoke(app, ["status", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"] == "state"
    assert "SECRET" not in result.output


@pytest.mark.parametrize("args", [[], ["--export", "x", "--from-archive"]])
def test_import_selectors_are_usage_error(local, args):
    result = CliRunner().invoke(app, ["import", *args, "--json"])
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"] == "usage"
    assert not local.exists()


@pytest.mark.parametrize(
    "args, expected",
    [
        (["status"], "Latest state"),
        (["import", "--from-archive"], "Imported:"),
    ],
)
def test_text_output(local, monkeypatch, tmp_path, args, expected):
    from tests.fakes.store import InMemoryMemoryStore

    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(tmp_path / "archive"))
    monkeypatch.setattr(
        "engineering_memory.cli.runtime.make_memory", lambda _: InMemoryMemoryStore()
    )
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    assert expected in result.stdout


@pytest.mark.parametrize("path", ["", "   "])
def test_offline_status_rejects_blank_path(local, monkeypatch, path):
    monkeypatch.setenv("ENGINEERING_MEMORY_IMPORT_STATE_PATH", path)
    result = CliRunner().invoke(app, ["status", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"] == "configuration"


def test_status_uses_database_readonly_connection(local, monkeypatch):
    from sqlalchemy import event

    from engineering_memory import cli

    state = SQLiteImportState(local)
    state.initialize()
    state.close()
    engines = []
    original = SQLiteImportState.__init__

    def inspect_mode(self, *args, **kwargs):
        original(self, *args, **kwargs)
        engines.append(self._engine)

        @event.listens_for(self._engine, "connect")
        def forbid_write(connection, _):
            # SQLite must enforce that this connection cannot mutate the database.
            with pytest.raises(sqlite3.OperationalError):
                connection.execute("DELETE FROM import_records")

    monkeypatch.setattr(cli.runtime.SQLiteImportState, "__init__", inspect_mode)
    result = CliRunner().invoke(app, ["status", "--json"])
    assert result.exit_code == 0, result.output
    assert engines
