"""Claude through the real CLI, shared local adapters and replaceable memory."""

import json

import pytest
from typer.testing import CliRunner

from engineering_memory.access.service import MemoryAccess
from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.cli import app
from tests.fakes.store import InMemoryMemoryStore
from tests.synthetic import chatgpt_export, claude_export


@pytest.fixture
def configured(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGINEERING_MEMORY_IMPORT_STATE_PATH", str(tmp_path / "state.db"))
    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(tmp_path / "archive"))
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_LLM__BASE_URL", "http://proxy")
    memory = InMemoryMemoryStore()
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", lambda _: memory)
    return tmp_path, memory


def invoke(args, code=0):
    result = CliRunner().invoke(app, ["import", *args, "--json"])
    assert result.exit_code == code, (result.output, result.exception)
    return json.loads(result.stdout)


def test_import_mixed_recall_skip_changed_force_and_replay(configured):
    root, memory = configured
    path = claude_export.write(
        root / "conversations.json",
        [claude_export.record("shared", "Synthetic cobalt relay password=synthetic-secret-123")],
    )
    args = ["--source", "claude-chat", "--export", str(path)]
    assert invoke(args)["imported"] == 1
    assert invoke(args)["skipped"] == 1
    chat = chatgpt_export.write_directory(
        root / "chatgpt",
        [
            chatgpt_export.linear_record(
                "shared", chatgpt_export.message("user", "Synthetic cobalt relay ChatGPT fact")
            )
        ],
    )
    assert invoke(["--export", str(chat)])["imported"] == 1
    assert set(memory.retained) == {"chatgpt:shared", "claude-chat:shared"}
    archive = LocalRawArchive(root / "archive")
    access = MemoryAccess(memory, archive)
    assert len(access.search_memory(query="cobalt relay")["results"]) == 2
    found = access.search_memory(query="cobalt relay", tags=["source:claude-chat"])["results"]
    assert len(found) == 1 and found[0]["document_id"] == "claude-chat:shared"
    assert "synthetic-secret-123" not in json.dumps(found)
    opened = access.get_conversation(document_id="claude-chat:shared")
    assert "synthetic-secret-123" not in json.dumps(opened)
    assert b"synthetic-secret-123" in archive.load_original("claude-chat:shared").content
    claude_export.write(path, [claude_export.record("shared", "Changed cobalt relay")])
    assert invoke(args)["imported"] == 1
    path.unlink()
    assert invoke(["--source", "claude-chat", "--from-archive", "--force"])["imported"] == 1
    assert (
        archive.load("claude-chat:shared").conversation.messages[0].text == "Changed cobalt relay"
    )
    assert invoke(["--source", "claude-chat", "--from-archive"])["skipped"] == 1


def test_preview_zero_writes_or_memory_calls(configured, monkeypatch):
    root, _ = configured

    def forbidden(_):
        pytest.fail("preview constructed memory")

    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", forbidden)
    path = claude_export.write(root / "conversations.json", [claude_export.record()])
    assert (
        invoke(["--source", "claude-chat", "--export", str(path), "--dry-run"])["would_import"] == 1
    )
    assert not (root / "state.db").exists()
    assert not (root / "archive").exists()


@pytest.mark.parametrize("source", ["claude-code", "codex", "hermes", "invalid"])
def test_unsupported_source_refused_before_side_effects(configured, monkeypatch, source):
    root, _ = configured

    def forbidden():
        pytest.fail("usage error loaded configuration")

    monkeypatch.setattr("engineering_memory.cli.runtime.load_settings", forbidden)
    data = invoke(["--source", source, "--export", "absent.json"], 2)
    assert data["error"] == "usage"
    assert not (root / "state.db").exists()


def test_bad_record_between_valid_ones(configured):
    root, _ = configured
    path = claude_export.write(
        root / "conversations.json",
        [claude_export.record("a"), {"uuid": "bad"}, claude_export.record("b")],
    )
    result = invoke(["--source", "claude-chat", "--export", str(path)], 1)
    assert (result["imported"], result["failed"]) == (2, 1)
    assert result["outcomes"][1]["source_id"] == "bad"
