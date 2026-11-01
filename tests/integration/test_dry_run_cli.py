"""Dry-run CLI acceptance: offline, read-only, parity and safe presentation."""

import json

import pytest
from typer.testing import CliRunner

from engineering_memory.cli import app
from tests.fakes.store import InMemoryMemoryStore
from tests.synthetic import chatgpt_export as synth


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setattr("engineering_memory.settings.DEFAULT_ENV_FILE", None)
    for key, value in {
        "IMPORT_STATE_PATH": str(tmp_path / "state.db"),
        "ARCHIVE_ROOT": str(tmp_path / "archive"),
        "HINDSIGHT__BASE_URL": "http://unreachable.invalid",
        "LLM__BASE_URL": "http://unreachable.invalid",
    }.items():
        monkeypatch.setenv("ENGINEERING_MEMORY_" + key, value)
    return tmp_path


def invoke(args, code=0):
    result = CliRunner().invoke(app, ["import", *args, "--dry-run", "--json"])
    assert result.exit_code == code, (result.output, result.exception)
    return json.loads(result.stdout)


def write_export(local, records=None):
    path = local / "export"
    synth.write_directory(
        path,
        records
        if records is not None
        else [synth.linear_record("one", synth.message("user", "safe synthetic fact"))],
    )
    return path


def poison(*args, **kwargs):
    raise AssertionError("forbidden durable/network call")


def test_missing_state_preview_never_constructs_memory_or_writes(local, monkeypatch):
    path = write_export(local)
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", poison)
    monkeypatch.setattr(
        "engineering_memory.ingestion.sqlite_state.SQLiteImportState.initialize", poison
    )
    monkeypatch.setattr(
        "engineering_memory.ingestion.sqlite_state.SQLiteImportState.record", poison
    )
    monkeypatch.setattr("engineering_memory.archive.local.LocalRawArchive.store", poison)
    data = invoke(["--export", str(path)])
    assert data["dry_run"] is True
    assert (data["would_import"], data["would_skip"], data["failed"]) == (1, 0, 0)
    assert "imported" not in data
    row = data["outcomes"][0]
    assert row["document_id"] == "chatgpt:one"
    assert row["project"] == "project:unknown"
    assert row["timestamp"]
    assert row["redaction_categories"] == []
    assert row["decision"] == "would_import"
    assert not (local / "state.db").exists()
    assert not (local / "archive").exists()


def test_preview_real_parity_and_readonly_replay(local, monkeypatch):
    item = synth.linear_record("one", synth.message("user", "safe synthetic fact"))
    path = write_export(local, [item])
    data = invoke(["--export", str(path)])
    assert [r["decision"] for r in data["outcomes"]] == ["would_import"]
    monkeypatch.setattr(
        "engineering_memory.cli.runtime.make_memory", lambda _: InMemoryMemoryStore()
    )
    real = CliRunner().invoke(app, ["import", "--export", str(path), "--json"])
    assert real.exit_code == 0, real.output
    actual = json.loads(real.stdout)
    assert (actual["imported"], actual["skipped"]) == (data["would_import"], data["would_skip"])
    before = {str(p.relative_to(local)): p.read_bytes() for p in local.rglob("*") if p.is_file()}
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", poison)
    assert invoke(["--export", str(path)])["would_skip"] == 1
    assert invoke(["--from-archive"])["would_skip"] == 1
    assert invoke(["--from-archive", "--force"])["would_import"] == 1
    after = {str(p.relative_to(local)): p.read_bytes() for p in local.rglob("*") if p.is_file()}
    assert before == after


@pytest.mark.parametrize("args", [[], ["--export", "x", "--from-archive"]])
def test_dry_run_usage_envelope(local, args):
    data = invoke(args, 2)
    assert data["dry_run"] and data["error"] == "usage"
    assert data["outcomes"] == []


def test_empty_missing_and_corrupt_input(local):
    path = write_export(local, [])
    assert invoke(["--export", str(path)])["would_import"] == 0
    assert invoke(["--export", str(local / "missing")], 1)["terminal_error"] == "source"
    (local / "state.db").write_bytes(b"PRIVATE-CANARY")
    data = invoke(["--export", str(path)], 1)
    assert data["error"] == "state"
    assert "PRIVATE-CANARY" not in json.dumps(data)


def test_text_preview_includes_per_conversation_metadata(local):
    path = write_export(local)
    result = CliRunner().invoke(app, ["import", "--export", str(path), "--dry-run"])
    assert result.exit_code == 0, result.output
    for value in ["Dry run", "chatgpt:one", "project:unknown", "would_import"]:
        assert value in result.stdout


def test_real_sanitizer_categories_and_no_canary_in_output(local, capsys):
    from tests.synthetic.secrets import SAMPLES

    samples = SAMPLES[:3]
    path = write_export(
        local,
        [
            synth.linear_record(
                "one", synth.message("user", "\n".join(sample.sentence for sample in samples))
            )
        ],
    )
    data = invoke(["--export", str(path)])
    assert data["outcomes"][0]["redaction_categories"] == sorted(
        {s.category.value for s in samples}
    )
    captured = json.dumps(data) + capsys.readouterr().err
    assert all(sample.value not in captured for sample in samples)


def test_recoverable_source_failure_continues(local):
    item = synth.linear_record("one", synth.message("user", "safe"))
    path = write_export(
        local, [item, item, synth.linear_record("last", synth.message("user", "last"))]
    )
    data = invoke(["--export", str(path)], 1)
    assert data["status"] == "partial_success"
    assert [r["decision"] for r in data["outcomes"]] == ["would_import", "failed", "would_import"]
    assert data["outcomes"][1]["error"] == "source"
    assert not (local / "state.db").exists()


@pytest.mark.parametrize("interrupt", [False, True])
def test_terminal_failure_or_interrupt_releases_reader(local, monkeypatch, interrupt):
    from engineering_memory.ingestion.chatgpt import ChatGPTExportSource

    path = write_export(local)
    original = ChatGPTExportSource.read
    closed = []

    def broken(source):
        reader = original(source)
        try:
            yield next(reader)
            if interrupt:
                raise KeyboardInterrupt()
            raise OSError("PRIVATE-CANARY")
        finally:
            reader.close()
            closed.append(True)

    monkeypatch.setattr(ChatGPTExportSource, "read", broken)
    data = invoke(["--export", str(path)], 130 if interrupt else 1)
    assert closed
    assert data["error"] == ("interrupted" if interrupt else None)
    if not interrupt:
        assert data["would_import"] == 1 and data["terminal_error"] == "source"
    assert "PRIVATE-CANARY" not in json.dumps(data)
    assert not (local / "state.db").exists()
