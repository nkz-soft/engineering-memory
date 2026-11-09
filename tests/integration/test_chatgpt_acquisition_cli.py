import json
import sqlite3
from zipfile import ZipFile, ZipInfo

import pytest
from typer.testing import CliRunner

from engineering_memory.cli import app
from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from tests.fakes.store import InMemoryMemoryStore
from tests.synthetic import chatgpt_export as synth


@pytest.fixture
def configured(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for name, value in {
        "IMPORT_STATE_PATH": tmp_path / "state.db",
        "ARCHIVE_ROOT": tmp_path / "archive",
        "CHATGPT_EXPORT_INBOX": inbox,
        "HINDSIGHT__BASE_URL": "http://engine",
        "LLM__BASE_URL": "http://proxy",
    }.items():
        monkeypatch.setenv(f"ENGINEERING_MEMORY_{name}", str(value))
    return tmp_path


def invoke(*args, code=0):
    result = CliRunner().invoke(app, [*args, "--json"])
    assert result.exit_code == code, (result.output, result.exception)
    return json.loads(result.stdout)


def write_export(path, *, day=2, records=None):
    if records is None:
        records = [synth.linear_record("a", synth.message("user", "synthetic test"))]
    with ZipFile(path, "w") as output:
        member = ZipInfo("conversations.json", (2025, 1, day, 3, 4, 6))
        output.writestr(member, json.dumps(records))


def test_watcher_imports_then_deduplicates_renamed_archive(configured, monkeypatch):
    memory = InMemoryMemoryStore()
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", lambda _: memory)
    inbox = configured / "inbox"
    path = inbox / "new.zip"
    write_export(path)
    original = path.read_bytes()
    assert invoke("acquire-chatgpt")["outcome"] == "empty"
    assert not (configured / "state.db").exists()
    assert invoke("acquire-chatgpt")["imported"] == 1
    (blob,) = (configured / "archive").rglob("*.zip")
    assert blob.read_bytes() == original
    assert invoke("acquire-chatgpt")["outcome"] == "empty"
    path.rename(inbox / "renamed.zip")
    assert invoke("acquire-chatgpt")["outcome"] == "empty"
    assert invoke("acquire-chatgpt")["outcome"] == "duplicate"
    assert list(memory.retained) == ["chatgpt:a"]


def test_truncated_inbox_leaves_previous_state(configured, monkeypatch):
    memory = InMemoryMemoryStore()
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", lambda _: memory)
    valid = configured / "valid.zip"
    write_export(valid)
    assert invoke("acquire-chatgpt", "--file", str(valid))["imported"] == 1
    before = invoke("status")
    broken = configured / "inbox" / "private-name.zip"
    broken.write_bytes(valid.read_bytes()[:-22])
    assert invoke("acquire-chatgpt")["outcome"] == "empty"
    monkeypatch.setattr(
        "engineering_memory.cli.runtime.make_memory", lambda _: pytest.fail("ingestion started")
    )
    report = invoke("acquire-chatgpt", code=1)
    assert report["error"] == "invalid_export"
    assert "private-name" not in json.dumps(report)
    assert invoke("status") == before
    assert len(list((configured / "archive").rglob("*.zip"))) == 1


def test_recovery_uses_archived_copy_and_skips_completed_work(configured, monkeypatch):
    class FailsOnce(InMemoryMemoryStore):
        failing = True

        def retain(self, enriched):
            if self.failing and enriched.document_id == "chatgpt:b":
                raise RuntimeError("private failure")
            super().retain(enriched)

    memory = FailsOnce()
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", lambda _: memory)
    path = configured / "inbox" / "pending.zip"
    write_export(
        path,
        records=[
            synth.linear_record(key, synth.message("user", f"synthetic {key}"))
            for key in ("a", "b")
        ],
    )
    assert invoke("acquire-chatgpt")["outcome"] == "empty"
    failure = invoke("acquire-chatgpt", code=1)
    assert (failure["imported"], failure["failed"]) == (1, 1)
    assert invoke("status")["last_chatgpt_export"] is None
    path.unlink()
    memory.failing = False
    resumed = invoke("acquire-chatgpt")
    assert (resumed["imported"], resumed["skipped"]) == (1, 1)
    assert invoke("status")["last_chatgpt_export"]["ingested_at"]


def test_status_production_evidence_and_stale_rejection(configured, monkeypatch):
    monkeypatch.setattr(
        "engineering_memory.cli.runtime.make_memory", lambda _: InMemoryMemoryStore()
    )
    monkeypatch.setenv("ENGINEERING_MEMORY_CHATGPT_EXPORT_ZIP_OFFSET_MINUTES", "0")
    current = configured / "current.zip"
    write_export(current)
    assert invoke("acquire-chatgpt", "--file", str(current))["imported"] == 1
    status = invoke("status")["last_chatgpt_export"]
    assert status["produced_at"].replace("+00:00", "Z") == "2025-01-02T03:04:06Z"
    assert status["production_evidence"] == "zip_member_estimate"
    result = CliRunner().invoke(app, ["status"])
    assert "2025-01-02T03:04:06" in result.stdout
    assert "zip_member_estimate" in result.stdout
    older = configured / "older.zip"
    write_export(older, day=1)
    assert invoke("acquire-chatgpt", "--file", str(older), code=1)["error"] == "stale_export"
    assert invoke("status")["last_chatgpt_export"] == status
    monkeypatch.delenv("ENGINEERING_MEMORY_CHATGPT_EXPORT_ZIP_OFFSET_MINUTES")
    newest = configured / "unknown.zip"
    write_export(newest, day=3)
    assert invoke("acquire-chatgpt", "--file", str(newest))["skipped"] == 1
    assert invoke("status")["last_chatgpt_export"]["produced_at"] is None


def test_v1_status_and_preview_are_read_only_and_acquisition_migrates(configured, monkeypatch):
    path = configured / "state.db"
    state = SQLiteImportState(path)
    state.initialize()
    state.close()
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE IF EXISTS export_acquisitions")
        conn.execute("UPDATE import_state_schema SET version=1")
    before = path.read_bytes()
    assert invoke("status")["last_chatgpt_export"] is None
    export = configured / "valid.zip"
    write_export(export)
    assert invoke("import", "--export", str(export), "--dry-run")["would_import"] == 1
    assert path.read_bytes() == before
    monkeypatch.setattr(
        "engineering_memory.cli.runtime.make_memory", lambda _: InMemoryMemoryStore()
    )
    assert invoke("acquire-chatgpt", "--file", str(export))["imported"] == 1
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT version FROM import_state_schema").fetchone() == (2,)
        assert conn.execute("SELECT count(*) FROM export_acquisitions").fetchone() == (1,)


def test_failure_recording_acquisition_reuses_the_published_blob(configured, monkeypatch):
    from engineering_memory.ingestion.state import ImportStateUnavailable

    source = configured / "export.zip"
    write_export(source)

    def unavailable(*_):
        raise ImportStateUnavailable("test injection")

    with monkeypatch.context() as patch:
        patch.setattr(SQLiteImportState, "record_acquisition", unavailable)
        patch.setattr(
            "engineering_memory.cli.runtime.make_memory", lambda _: pytest.fail("ingestion started")
        )
        assert invoke("acquire-chatgpt", "--file", str(source), code=1)["error"] == "state"
    (published,) = (configured / "archive").rglob("*.zip")
    assert published.read_bytes() == source.read_bytes()
    monkeypatch.setattr(
        "engineering_memory.cli.runtime.make_memory", lambda _: InMemoryMemoryStore()
    )
    source.unlink()
    assert invoke("acquire-chatgpt")["imported"] == 1
    assert list((configured / "archive").rglob("*.zip")) == [published]


def test_completion_write_failure_resumes_without_retain(configured, monkeypatch):
    from engineering_memory.ingestion.state import ImportStateUnavailable

    source = configured / "export.zip"
    write_export(source)
    memory = InMemoryMemoryStore()
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", lambda _: memory)

    def unavailable(*_):
        raise ImportStateUnavailable("test injection")

    with monkeypatch.context() as patch:
        patch.setattr(SQLiteImportState, "complete_acquisition", unavailable)
        assert invoke("acquire-chatgpt", "--file", str(source), code=1)["error"] == "state"
    assert list(memory.retained) == ["chatgpt:a"]
    assert invoke("status")["last_chatgpt_export"] is None
    source.unlink()
    assert invoke("acquire-chatgpt")["skipped"] == 1
    assert invoke("status")["last_chatgpt_export"]["ingested_at"]


def test_v1_migration_rolls_back_if_new_schema_validation_fails(configured, monkeypatch):
    from engineering_memory.ingestion.state import ImportStateCorrupt

    path = configured / "state.db"
    state = SQLiteImportState(path)
    state.initialize()
    state.close()
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE export_acquisitions")
        conn.execute("UPDATE import_state_schema SET version=1")

    validate = state._validate_schema

    def reject_migrated(connection):
        version = validate(connection)
        if version == 2:
            raise ImportStateCorrupt("test injection")
        return version

    monkeypatch.setattr(state, "_validate_schema", reject_migrated)
    try:
        with pytest.raises(ImportStateCorrupt):
            state.initialize()
        with sqlite3.connect(path) as conn:
            assert conn.execute("SELECT version FROM import_state_schema").fetchone() == (1,)
            assert (
                conn.execute(
                    "SELECT name FROM sqlite_master WHERE name='export_acquisitions'"
                ).fetchone()
                is None
            )
    finally:
        state.close()
