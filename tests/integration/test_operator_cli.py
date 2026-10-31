"""Commands over real local adapters and a replaceable memory engine."""

import json
import os
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from engineering_memory.cli import app
from tests.fakes.store import InMemoryMemoryStore
from tests.synthetic import chatgpt_export as synth


@pytest.fixture
def configured(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGINEERING_MEMORY_IMPORT_STATE_PATH", str(tmp_path / "state.db"))
    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(tmp_path / "archive"))
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_LLM__BASE_URL", "http://proxy")
    return tmp_path


def invoke(args, code=0):
    result = CliRunner().invoke(app, [*args, "--json"])
    assert result.exit_code == code, (result.output, result.exception)
    return json.loads(result.stdout)


def corpus(path, text="safe synthetic fact"):
    synth.write_directory(path, [synth.linear_record("cli-one", synth.message("user", text))])


def test_export_skip_changed_force_and_replay(configured, monkeypatch):
    memory = InMemoryMemoryStore()
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", lambda _: memory)
    path = configured / "export"
    corpus(path)
    assert invoke(["import", "--export", str(path)])["imported"] == 1
    assert invoke(["import", "--export", str(path)])["skipped"] == 1
    corpus(path, "changed synthetic fact")
    assert invoke(["import", "--export", str(path)])["imported"] == 1
    assert invoke(["import", "--from-archive", "--force"])["imported"] == 1
    data = invoke(["status"])
    assert (data["imported"], data["failed"]) == (1, 0)
    assert list(memory.retained) == ["chatgpt:cli-one"]
    assert memory.recall("changed synthetic fact")


def test_mixed_run_continues_and_reports_failure(configured, monkeypatch):
    class RejectOne(InMemoryMemoryStore):
        def retain(self, enriched):
            if enriched.document_id == "chatgpt:bad":
                raise RuntimeError("SECRET-CONTENT")
            super().retain(enriched)

    memory = RejectOne()
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", lambda _: memory)
    path = configured / "export"
    synth.write_directory(
        path,
        [
            synth.linear_record("bad", synth.message("user", "first")),
            synth.linear_record("good", synth.message("user", "second")),
        ],
    )
    data = invoke(["import", "--export", str(path)], 1)
    assert (data["imported"], data["failed"], data["status"]) == (1, 1, "partial_success")
    assert data["outcomes"][0]["error"] == "retain"
    assert "SECRET-CONTENT" not in json.dumps(data)
    assert invoke(["status"])["failed"] == 1


def test_empty_and_missing_source(configured, monkeypatch):
    monkeypatch.setattr(
        "engineering_memory.cli.runtime.make_memory", lambda _: InMemoryMemoryStore()
    )
    path = configured / "empty"
    synth.write_directory(path, [])
    assert invoke(["import", "--export", str(path)])["imported"] == 0
    data = invoke(["import", "--export", str(configured / "absent")], 1)
    assert data["terminal_error"] == "source"


@pytest.mark.skipif(
    os.environ.get("ENGINEERING_MEMORY_LIVE_CONTRACT") != "1",
    reason="requires isolated live contract stack",
)
def test_live_commands(configured, monkeypatch):
    import httpx

    url = os.environ.get("ENGINEERING_MEMORY_LIVE_STORE_URL", "http://127.0.0.1:8889")
    bank = "synthetic-cli-" + uuid4().hex
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", url)
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BANK_ID", bank)
    path = configured / "export"
    corpus(path, "Synthetic contract fact: Orchard CLI fixture uses a cobalt relay.")
    try:
        assert invoke(["provision"])["mission_verified"]
        assert invoke(["import", "--export", str(path)])["imported"] == 1
        assert invoke(["import", "--export", str(path)])["skipped"] == 1
        assert invoke(["import", "--from-archive", "--force"])["imported"] == 1
        assert invoke(["status"])["imported"] == 1
        from engineering_memory.memory.hindsight.store import HindsightStore
        from engineering_memory.settings import load_settings

        with HindsightStore(load_settings().hindsight) as store:
            found = store.recall("cobalt relay")
            assert any("cobalt relay" in item.content for item in found)
    finally:
        with httpx.Client(base_url=url, trust_env=False) as client:
            client.delete(f"/v1/default/banks/{bank}").raise_for_status()


def test_interrupt_releases_memory_and_source(configured, monkeypatch):
    from engineering_memory.ingestion.chatgpt import source as source_module

    closed = []

    class Interrupted(InMemoryMemoryStore):
        def retain(self, enriched):
            raise KeyboardInterrupt()

        def close(self):
            closed.append("memory")

    original_close = source_module._Reader.close

    def close_reader(reader):
        closed.append("reader")
        original_close(reader)

    monkeypatch.setattr(source_module._Reader, "close", close_reader)
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", lambda _: Interrupted())
    path = configured / "export"
    corpus(path)
    data = invoke(["import", "--export", str(path)], 130)
    assert data["error"] == "interrupted"
    assert "reader" in closed and "memory" in closed


def test_terminal_source_failure_preserves_progress(configured, monkeypatch):
    from engineering_memory.ingestion.chatgpt import ChatGPTExportSource

    monkeypatch.setattr(
        "engineering_memory.cli.runtime.make_memory", lambda _: InMemoryMemoryStore()
    )
    path = configured / "export"
    corpus(path)
    read = ChatGPTExportSource.read

    def broken_read(source):
        reader = read(source)
        try:
            yield next(reader)
            raise OSError("SECRET")
        finally:
            reader.close()

    monkeypatch.setattr(ChatGPTExportSource, "read", broken_read)
    data = invoke(["import", "--export", str(path)], 1)
    assert data["status"] == "partial_success"
    assert data["imported"] == 1 and data["terminal_error"] == "source"
    assert len(data["outcomes"]) == 1


def test_state_write_failure_is_reported_and_closes_resources(configured, monkeypatch):
    from engineering_memory.ingestion.sqlite_state import SQLiteImportState

    memory = InMemoryMemoryStore()
    closed = []
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", lambda _: memory)
    original_close = SQLiteImportState.close

    def close(state):
        closed.append(True)
        original_close(state)

    def fail_record(*_):
        raise OSError("SECRET")

    monkeypatch.setattr(SQLiteImportState, "record", fail_record)
    monkeypatch.setattr(SQLiteImportState, "close", close)
    path = configured / "export"
    corpus(path)
    data = invoke(["import", "--export", str(path)], 1)
    assert data["failed"] == 1
    assert data["outcomes"][0]["error"] == "state_write"
    assert data["outcomes"][0]["state_record_failed"] is True
    assert list(memory.retained) == ["chatgpt:cli-one"]
    assert closed
