"""Durability, corruption and privacy checks using real local SQLite files."""

import sqlite3
import subprocess
import sys
from datetime import datetime

import pytest
from sqlalchemy import event

from engineering_memory.ingestion import ImportStateCorrupt, ImportStateUnavailable
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.normalization import Source
from tests.contracts.state import record


@pytest.fixture
def state(tmp_path):
    result = SQLiteImportState(tmp_path / "nested" / "state.db")
    result.initialize()
    yield result
    result.close()


def execute(path, sql):
    with sqlite3.connect(path) as db:
        db.execute(sql)


def test_construction_is_inert_and_validation_does_not_create(tmp_path):
    path = tmp_path / "missing" / "state.db"
    state = SQLiteImportState(path)
    assert not path.parent.exists()
    with pytest.raises(ImportStateUnavailable):
        state.validate()
    assert not path.parent.exists()
    with pytest.raises(ImportStateUnavailable):
        state.find(Source.CHATGPT, "one")


def test_initialize_is_repeatable_without_erasing_records(state):
    state.record(record())
    state.initialize()
    assert state.find(Source.CHATGPT, "abc123") == record()


def test_timestamp_and_opaque_identifier_round_trip(state):
    item = record(source_id="unicode-λ';DROP/**/TABLE/**/import_records;--").model_copy(
        update={"recorded_at": datetime.fromisoformat("2026-10-27T10:01:02.123456+03:00")}
    )
    state.record(item)
    assert state.find(item.source, item.source_id) == item
    assert state.find(Source.CHATGPT, "abc123") is None


def test_fresh_process_reads_committed_state(state):
    state.record(record())
    state.close()
    script = """
import sys
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from engineering_memory.normalization import Source
s = SQLiteImportState(sys.argv[1])
s.validate()
r = s.find(Source.CHATGPT, 'abc123')
assert r is not None and r.document_id == 'chatgpt:abc123'
assert r.status == 'imported'
s.close()
"""
    result = subprocess.run([sys.executable, "-c", script, str(state.path)], capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE import_state_schema SET version=99",
        "DELETE FROM import_state_schema",
        "DROP TABLE import_records",
        "ALTER TABLE import_records RENAME COLUMN source_id TO wrong",
    ],
)
def test_incompatible_storage_is_rejected_without_repair(state, sql):
    state.record(record())
    state.close()
    execute(state.path, sql)
    before = state.path.read_bytes()
    other = SQLiteImportState(state.path)
    with pytest.raises(ImportStateCorrupt):
        other.initialize()
    assert state.path.read_bytes() == before


def test_foreign_database_is_not_adopted(tmp_path):
    path = tmp_path / "foreign.db"
    execute(path, "CREATE TABLE foreign_data (value TEXT)")
    with pytest.raises(ImportStateCorrupt):
        SQLiteImportState(path).initialize()
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [
            ("foreign_data",)
        ]


def test_malformed_row_is_corrupt_not_unknown(state):
    state.record(record())
    execute(state.path, "UPDATE import_records SET recorded_at='not-a-time'")
    with pytest.raises(ImportStateCorrupt):
        state.find(Source.CHATGPT, "abc123")


def test_constraints_refuse_invalid_status_and_error_pairing(state):
    state.record(record())
    for change in ("status='skipped'", "status='failed'", "error='unexpected'"):
        with pytest.raises(sqlite3.IntegrityError):
            execute(state.path, f"UPDATE import_records SET {change}")
    assert state.find(Source.CHATGPT, "abc123") == record()


def test_failed_commit_rolls_back_complete_record(state):
    state.record(record())

    def fail_commit(connection):
        raise sqlite3.OperationalError("synthetic private diagnostic")

    event.listen(state._engine, "commit", fail_commit)
    try:
        with pytest.raises(ImportStateCorrupt):
            state.record(record(content_hash="changed"))
    finally:
        event.remove(state._engine, "commit", fail_commit)
    assert state.find(Source.CHATGPT, "abc123") == record()


def test_independent_reader_sees_updates(state):
    other = SQLiteImportState(state.path)
    other.validate()
    state.record(record())
    assert other.find(Source.CHATGPT, "abc123") == record()
    state.record(record(content_hash="new"))
    assert other.find(Source.CHATGPT, "abc123").content_hash == "new"
    other.close()


def test_removed_database_is_unavailable_and_not_recreated(state):
    state.path.unlink()
    with pytest.raises(ImportStateUnavailable):
        state.find(Source.CHATGPT, "abc123")
    assert not state.path.exists()


def test_database_failures_do_not_expose_driver_parameters(state, caplog, capsys):
    state.path.write_bytes(b"synthetic-private-diagnostic")
    with pytest.raises(ImportStateCorrupt) as raised:
        state.find(Source.CHATGPT, "synthetic-private-id")
    output = str(raised.value) + repr(raised.value) + caplog.text + capsys.readouterr().out
    assert "synthetic-private" not in output
    assert "SELECT" not in output


def test_reader_open_race_never_recreates_database(state, monkeypatch):
    require_file = state._require_file

    def disappear_after_check():
        require_file()
        state.path.unlink()

    monkeypatch.setattr(state, "_require_file", disappear_after_check)
    with pytest.raises(ImportStateUnavailable):
        state.find(Source.CHATGPT, "abc123")
    assert not state.path.exists()


def test_foreign_view_only_database_is_not_initialized(tmp_path):
    path = tmp_path / "view.db"
    execute(path, "CREATE VIEW foreign_view AS SELECT 'preserve' AS value")
    with pytest.raises(ImportStateCorrupt):
        SQLiteImportState(path).initialize()


@pytest.mark.parametrize(
    "sql",
    [
        "CREATE UNIQUE INDEX wrong_identity ON import_records(source_id)",
        "CREATE UNIQUE INDEX wrong_hash ON import_records(content_hash)",
        "CREATE UNIQUE INDEX wrong_expression ON import_records(lower(source_id))",
    ],
)
def test_extra_unique_indexes_are_incompatible(state, sql):
    execute(state.path, sql)
    with pytest.raises(ImportStateCorrupt):
        SQLiteImportState(state.path).validate()


def test_check_constraints_preserve_string_literal_case(state):
    state.close()
    with sqlite3.connect(state.path) as db:
        ddl = db.execute("SELECT sql FROM sqlite_master WHERE name='import_records'").fetchone()[0]
        db.execute("DROP TABLE import_records")
        db.execute(ddl.replace("'imported'", "'IMPORTED'"))
    with pytest.raises(ImportStateCorrupt):
        SQLiteImportState(state.path).validate()


def test_reader_sees_old_complete_record_during_uncommitted_write(state):
    state.record(record())
    reader = SQLiteImportState(state.path)
    reader.validate()
    with sqlite3.connect(state.path) as writer:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE import_records SET content_hash='new'")
        assert reader.find(Source.CHATGPT, "abc123") == record()
    assert reader.find(Source.CHATGPT, "abc123").content_hash == "new"
    reader.close()


def test_failed_initialization_commit_leaves_no_partial_schema(tmp_path):
    state = SQLiteImportState(tmp_path / "new.db")

    def fail_commit(connection):
        raise sqlite3.OperationalError("synthetic commit failure")

    event.listen(state._engine, "commit", fail_commit)
    try:
        with pytest.raises(ImportStateCorrupt):
            state.initialize()
    finally:
        event.remove(state._engine, "commit", fail_commit)
    with sqlite3.connect(state.path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
    state.initialize()
    state.record(record())
    assert state.find(Source.CHATGPT, "abc123") == record()
