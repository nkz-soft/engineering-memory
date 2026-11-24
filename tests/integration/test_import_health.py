"""Import health is durable, bounded operational metadata."""

import os
import sqlite3
import time
from datetime import UTC, datetime, timedelta

import pytest

from engineering_memory.cli import runtime
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.ingestion.state import ImportRecord
from engineering_memory.normalization import Source
from tests.contracts.conversations import conversation
from tests.fakes.store import InMemoryMemoryStore
from tests.integration.test_persistent_import_state import export_to

NOW = datetime(2026, 11, 19, tzinfo=UTC)


def open_state(path):
    state = SQLiteImportState(path, read_only=True)
    state.validate()
    return state


@pytest.mark.parametrize("version", [1, 2, 3])
def test_legacy_store_reads_empty_and_migrates(tmp_path, version):
    path = tmp_path / "state.db"
    state = SQLiteImportState(path)
    state.initialize()
    state.close()
    with sqlite3.connect(path, autocommit=False) as connection:
        connection.execute("DROP TABLE retain_receipts")
        if version < 3:
            connection.execute("DROP TABLE source_health")
            connection.execute("DROP TABLE project_import_health")
        if version == 1:
            connection.execute("DROP TABLE export_acquisitions")
        connection.execute("UPDATE import_state_schema SET version = ?", (version,))
    reader = open_state(path)
    assert reader.read_health("alpha") == ([], None)
    reader.close()
    state.initialize()
    assert state.read_health("alpha") == ([], None)


def test_success_and_attempt_ordering_are_independent(tmp_path):
    state = SQLiteImportState(tmp_path / "state.db")
    state.initialize()
    for stamp in (NOW, NOW - timedelta(seconds=1)):
        state.record_import(
            ImportRecord(
                source=Source.CHATGPT,
                source_id="private-id",
                content_hash="private-hash",
                document_id="chatgpt:private-id",
                recorded_at=stamp,
                status="imported",
            ),
            project="alpha",
            started_at=stamp - timedelta(seconds=2),
        )
    from engineering_memory.ingestion.health import SourceHealth

    state.record_attempt(
        SourceHealth(
            source=Source.CHATGPT,
            outcome="failed",
            last_attempt_at=NOW,
            error_categories=("source",),
        )
    )
    state.record_attempt(
        SourceHealth(
            source=Source.CHATGPT,
            outcome="healthy",
            last_attempt_at=NOW - timedelta(seconds=1),
        )
    )
    rows, evidence = open_state(state.path).read_health("alpha")
    assert evidence.completed_at == NOW
    assert evidence.started_at == NOW - timedelta(seconds=2)
    assert rows[0].last_success_at == NOW
    assert rows[0].outcome == "failed"
    assert open_state(state.path).read_health("beta")[1] is None
    assert "private" not in rows[0].model_dump_json()


def test_runtime_restart_failure_retry_and_dry_run(tmp_path, monkeypatch):
    path = tmp_path / "state.db"
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://fixture.invalid")
    monkeypatch.setenv("ENGINEERING_MEMORY_LLM__BASE_URL", "http://fixture.invalid")
    monkeypatch.setenv("ENGINEERING_MEMORY_IMPORT_STATE_PATH", str(path))
    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(tmp_path / "archive"))
    monkeypatch.setattr(runtime, "make_memory", lambda _: InMemoryMemoryStore())
    export = tmp_path / "export.json"
    export_to(export, conversation(text="PRIVATE_CONVERSATION_SENTINEL"))
    runtime.run_import(None, str(export), False, "test")
    runtime.run_import(None, str(tmp_path / "PRIVATE_MISSING_PATH"), False, "test", source="codex")
    reader = open_state(path)
    rows, _ = reader.read_health()
    health = {row.source: row for row in rows}
    assert health[Source.CHATGPT].outcome == "healthy"
    assert health[Source.CODEX].outcome == "failed"
    success = health[Source.CHATGPT].last_success_at
    assert success is not None
    assert "PRIVATE_" not in str(rows)

    runtime.run_import(None, str(tmp_path / "missing"), False, "test")
    rows, _ = reader.read_health()
    failed = next(row for row in rows if row.source == Source.CHATGPT)
    assert failed.outcome == "failed" and failed.last_success_at == success
    runtime.run_import(None, str(export), False, "test", dry_run=True)
    assert reader.read_health()[0] == rows
    runtime.run_import(None, str(export), False, "test")
    recovered = next(row for row in reader.read_health()[0] if row.source == Source.CHATGPT)
    assert recovered.outcome == "healthy"
    assert recovered.last_success_at == success
    assert not recovered.error_categories


def test_scheduled_import_keeps_deferred_and_partial_outcomes(tmp_path, monkeypatch):
    from engineering_memory.cli.results import result
    from tests.synthetic import codex

    path = tmp_path / "state.db"
    sessions = tmp_path / "sessions"
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://fixture.invalid")
    monkeypatch.setenv("ENGINEERING_MEMORY_LLM__BASE_URL", "http://fixture.invalid")
    monkeypatch.setenv("ENGINEERING_MEMORY_IMPORT_STATE_PATH", str(path))
    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(tmp_path / "archive"))
    monkeypatch.setenv("ENGINEERING_MEMORY_SESSION_IMPORT__CODEX_ROOT", str(sessions))
    monkeypatch.setenv(
        "ENGINEERING_MEMORY_SESSION_IMPORT__CLAUDE_CODE_ROOT",
        str(tmp_path / "missing"),
    )
    monkeypatch.setattr(runtime, "make_memory", lambda _: InMemoryMemoryStore())
    fixture = codex.write(sessions / "fixture.jsonl", codex.debugging())
    runtime.run_session_import(result("import-sessions"), "test")
    reader = open_state(path)
    rows = {row.source: row for row in reader.read_health()[0]}
    assert rows[Source.CODEX].outcome == "waiting"
    assert rows[Source.CODEX].deferred_count == 1
    assert rows[Source.CODEX].last_success_at is None
    assert rows[Source.CLAUDE_CODE].outcome == "failed"

    invalid = sessions / "invalid.jsonl"
    invalid.write_text("invalid")
    past = time.time() - 600
    os.utime(invalid, (past, past))
    os.utime(fixture, (past, past))
    runtime.run_session_import(result("import-sessions"), "test")
    rows = {row.source: row for row in reader.read_health()[0]}
    assert rows[Source.CODEX].outcome == "partial"
    assert rows[Source.CODEX].error_categories == ("source",)
    assert rows[Source.CODEX].last_success_at is not None
    assert rows[Source.CODEX].deferred_count == 0


def test_failed_attempt_write_does_not_abort_other_sources(tmp_path, monkeypatch):
    from engineering_memory.cli.results import result
    from engineering_memory.ingestion.state import ImportStateUnavailable

    state_path = tmp_path / "state.db"
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://fixture.invalid")
    monkeypatch.setenv("ENGINEERING_MEMORY_LLM__BASE_URL", "http://fixture.invalid")
    monkeypatch.setenv("ENGINEERING_MEMORY_IMPORT_STATE_PATH", str(state_path))
    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(tmp_path / "archive"))
    monkeypatch.setenv("ENGINEERING_MEMORY_SESSION_IMPORT__CODEX_ROOT", str(sessions))
    monkeypatch.setenv("ENGINEERING_MEMORY_SESSION_IMPORT__CLAUDE_CODE_ROOT", str(sessions))
    monkeypatch.setattr(runtime, "make_memory", lambda _: InMemoryMemoryStore())
    record = SQLiteImportState.record_attempt

    def fail_codex(store, health):
        if health.source == Source.CODEX:
            raise ImportStateUnavailable("PRIVATE_STATUS_PATH")
        record(store, health)

    monkeypatch.setattr(SQLiteImportState, "record_attempt", fail_codex)
    data = result("import-sessions")
    runtime.run_session_import(data, "test")
    assert [row["source"] for row in data["sources"]] == ["codex", "claude-code"]
    assert data["error"] == "state"
    assert data["status"] != "success"
    assert "PRIVATE_" not in str(data)
    reader = open_state(state_path)
    (observed,) = reader.read_health()[0]
    assert observed.source == Source.CLAUDE_CODE


def test_aggregate_write_failure_rolls_back_import_record(tmp_path, monkeypatch):
    from sqlalchemy.dialects.sqlite import insert

    from engineering_memory.ingestion import sqlite_state
    from engineering_memory.ingestion.state import ImportStateUnavailable

    state = SQLiteImportState(tmp_path / "state.db")
    state.initialize()

    def fail_project(table):
        if table.name == "project_import_health":
            raise ImportStateUnavailable("synthetic write failure")
        return insert(table)

    monkeypatch.setattr(sqlite_state, "insert", fail_project)
    record = ImportRecord(
        source="chatgpt",
        source_id="fixture",
        content_hash="hash",
        document_id="chatgpt:fixture",
        recorded_at=NOW,
        status="imported",
    )
    with pytest.raises(ImportStateUnavailable):
        state.record_import(record, project="alpha", started_at=NOW)
    assert state.find(Source.CHATGPT, "fixture") is None
    assert state.read_health("alpha") == ([], None)
