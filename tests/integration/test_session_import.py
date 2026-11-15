"""Scheduled and one-shot capture through the real CLI and local stores."""

import json
import os
import time

import pytest
from typer.testing import CliRunner

from engineering_memory.access.service import MemoryAccess
from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.cli import app
from tests.integration.test_claude_cli import configured, invoke  # noqa: F401
from tests.synthetic import claude_code, codex

PREFIX = "ENGINEERING_MEMORY_SESSION_IMPORT__"


def settle(path):
    old = time.time() - 600
    os.utime(path, (old, old))
    return path


def capture(code=0, *, structured=True):
    flags = ["--json"] if structured else []
    result = CliRunner().invoke(app, ["import-sessions", *flags])
    assert result.exit_code == code, (result.output, result.exception)
    return json.loads(result.stdout) if structured else result.output


def test_capture_both_native_layouts_and_reuse_identity(configured, monkeypatch):  # noqa: F811
    root, memory = configured
    codex_root, claude_root = root / "sessions", root / "projects"
    monkeypatch.setenv(PREFIX + "CODEX_ROOT", str(codex_root))
    monkeypatch.setenv(PREFIX + "CLAUDE_CODE_ROOT", str(claude_root))
    records = codex.debugging()
    path = settle(codex.write(codex_root / "2026/03/04/rollout-one.jsonl", records))
    claude_path = settle(
        claude_code.write(claude_root / "orchard/session.jsonl", claude_code.debugging())
    )
    settle(codex.write(codex_root / "other/cache/extra.jsonl", codex.debugging("out-of-layout")))
    settle(
        claude_code.write(
            claude_root / "orchard/subagents/extra.jsonl", claude_code.debugging("subagent")
        )
    )
    settle(codex.write(root / "outside.jsonl", codex.debugging("outside")))
    for index, metadata in enumerate(
        (
            {"source": {"subagent": "review"}},
            {"thread_source": "subagent"},
            {"source": {"internal": "guardian"}},
            {"thread_source": "memory_consolidation"},
        )
    ):
        child = codex.debugging(f"child-{index}")
        child[0]["payload"].update(metadata)
        settle(codex.write(path.parent / f"rollout-child-{index}.jsonl", child))
    retained = []
    original_retain = memory.retain

    def record_retain(item):
        retained.append(item.conversation.document_id)
        original_retain(item)

    monkeypatch.setattr(memory, "retain", record_retain)
    first = capture()
    assert [row["imported"] for row in first["sources"]] == [1, 1], first
    archive = LocalRawArchive(root / "archive")
    access = MemoryAccess(memory, archive)
    for kind, native in (("codex", path), ("claude-code", claude_path)):
        document_id = f"{kind}:session-one"
        found = access.search_memory(query="relay", tags=[f"source:{kind}"])["results"]
        assert [match["document_id"] for match in found] == [document_id]
        assert found[0]["started_at"].startswith("2026-03-04T09:30:00")
        opened = json.dumps(access.get_conversation(document_id=document_id))
        assert "port zero" in opened
        assert "synthetic-secret-123" not in opened
        assert archive.load_original(document_id).content == native.read_bytes()
    assert "codex: imported 0, unchanged 1" in capture(structured=False)
    assert len(retained) == 2
    assert [row["unchanged"] for row in capture()["sources"]] == [1, 1]
    assert len(retained) == 2

    records[4]["payload"]["output"] = "The updated cobalt relay listens on port 8123."
    settle(codex.write(path, records))
    assert capture()["sources"][0]["imported"] == 1
    assert retained[-1] == "codex:session-one" and len(retained) == 3
    path.unlink()
    assert invoke(["--source", "codex", "--from-archive", "--force"])["imported"] == 1
    assert "port 8123" in archive.load("codex:session-one").model_dump_json()


def test_capture_isolates_errors_and_retries(configured, monkeypatch):  # noqa: F811
    root, memory = configured
    codex_root = root / "private-sessions"
    monkeypatch.setenv(PREFIX + "CODEX_ROOT", str(codex_root))
    monkeypatch.setenv(PREFIX + "CLAUDE_CODE_ROOT", str(root / "missing-private-root"))
    recent = codex.write(codex_root / "recent.jsonl", codex.debugging("recent"))
    broken = codex_root / "private-malformed.jsonl"
    broken.write_text("private-invalid-content")
    settle(broken)
    settle(codex.write(codex_root / "settled.jsonl", codex.debugging("settled")))
    data = capture(1)
    assert data["status"] == "partial_success", data
    codex_result, claude_result = data["sources"]
    assert [codex_result[key] for key in ("imported", "unchanged", "deferred", "failed")] == [
        1,
        0,
        1,
        1,
    ]
    assert claude_result["error"] == "source_unavailable"
    assert "private-" not in json.dumps(data)
    assert set(memory.retained) == {"codex:settled"}
    monkeypatch.delenv(PREFIX + "CLAUDE_CODE_ROOT")
    settle(recent)
    settle(codex.write(broken, codex.debugging("repaired")))
    assert capture()["sources"][0]["imported"] == 2


@pytest.mark.parametrize("settings", [{}, {"CODEX_ROOT": " "}, {"QUIET_SECONDS": "0"}])
def test_invalid_or_missing_capture_settings_do_not_write(configured, monkeypatch, settings):  # noqa: F811
    root, _ = configured
    for name in ("CODEX_ROOT", "CLAUDE_CODE_ROOT", "QUIET_SECONDS"):
        monkeypatch.delenv(PREFIX + name, raising=False)
    for name, value in settings.items():
        monkeypatch.setenv(PREFIX + name, value)
    assert capture(1)["error"] == "configuration"
    assert not (root / "state.db").exists()
    assert not (root / "archive").exists()
