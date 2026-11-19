"""Real CLI/archive/state composition for Claude Code history."""

import json

import pytest

from engineering_memory.access.service import MemoryAccess
from engineering_memory.archive.local import LocalRawArchive
from tests.integration.test_claude_cli import configured, invoke  # noqa: F401
from tests.synthetic import claude_code as synth


def test_import_evidence_provenance_skip_update_and_archive_replay(configured):  # noqa: F811
    root, memory = configured
    records = synth.debugging()
    records[0]["repository"] = "https://example.test/org/orchard.git"
    path = synth.write(root / "one.jsonl", records)
    args = ["--source", "claude-code", "--export", str(path)]
    assert invoke(args)["imported"] == 1
    archive = LocalRawArchive(root / "archive")
    saved = archive.load("claude-code:session-one")
    assert saved.provenance.project == "orchard"
    assert saved.provenance.repository == "https://example.test/org/orchard.git"
    assert {str(t) for t in saved.tags} >= {"source:claude-code", "project:orchard"}
    assert invoke(args)["skipped"] == 1
    access = MemoryAccess(memory, archive)
    found = access.search_memory(query="relay", tags=["source:claude-code", "project:orchard"])
    assert found["results"][0]["document_id"] == "claude-code:session-one"
    opened = json.dumps(access.get_conversation(document_id="claude-code:session-one"))
    assert "port zero" in opened and "new_string" in opened
    assert "synthetic-secret-123" not in opened
    assert b"synthetic-secret-123" in archive.load_original("claude-code:session-one").content
    records[2]["message"]["content"][1]["content"] = "Updated failure"
    synth.write(path, records)
    assert invoke(args)["imported"] == 1
    path.unlink()
    assert invoke(["--source", "claude-code", "--from-archive", "--force"])["imported"] == 1
    assert len(memory.retained) == 1
    assert "Updated failure" in archive.load("claude-code:session-one").model_dump_json()
    assert invoke(["--source", "claude-code", "--from-archive"])["skipped"] == 1


def test_preview_no_writes_or_memory_construction(configured, monkeypatch):  # noqa: F811
    root, _ = configured
    monkeypatch.setattr(
        "engineering_memory.cli.runtime.make_memory",
        lambda _: pytest.fail("dry-run constructed memory"),
    )
    path = synth.write(root / "one.jsonl", synth.debugging())
    data = invoke(["--source", "claude-code", "--export", str(path), "--dry-run"])
    assert data["would_import"] == 1
    assert not (root / "state.db").exists()
    assert not (root / "archive").exists()


def test_bad_file_does_not_abort_batch(configured):  # noqa: F811
    root, _ = configured
    folder = root / "sessions"
    synth.write(folder / "a.jsonl", [{"type": "user", "PRIVATE": "PRIVATE"}])
    synth.write(folder / "b.jsonl", synth.debugging())
    data = invoke(["--source", "claude-code", "--export", str(folder)], 1)
    assert (data["imported"], data["failed"]) == (1, 1)
    assert "PRIVATE" not in json.dumps(data)


def test_each_session_has_own_sanitized_repository(configured):  # noqa: F811
    root, _ = configured
    folder = root / "sessions"
    for index, name in enumerate(("orchard", "lantern")):
        records = synth.debugging(f"session-{index}")
        records[0]["repository"] = (
            f"https://example.test/{name}.git password=" + "synthetic-secret-123"
        )
        synth.write(folder / f"{index}.jsonl", records)
    assert invoke(["--source", "claude-code", "--export", str(folder)])["imported"] == 2
    archive = LocalRawArchive(root / "archive")
    for index, name in enumerate(("orchard", "lantern")):
        saved = archive.load(f"claude-code:session-{index}")
        assert name in saved.provenance.repository
        assert "synthetic-secret-123" not in saved.model_dump_json()


def test_archive_refuses_wrong_identity_and_advances(configured):  # noqa: F811
    from unittest.mock import Mock

    from engineering_memory.archive import OriginalPayload
    from engineering_memory.ingestion.claude_code.archive_source import ClaudeCodeArchiveSource
    from engineering_memory.ingestion.source import SourceFormatError

    archive = Mock()
    archive.iter_document_ids.return_value = iter(["claude-code:wrong", "claude-code:session-one"])
    archive.load_original.return_value = OriginalPayload(
        content=synth.encode(synth.debugging()), media_type="application/x-ndjson"
    )
    reader = ClaudeCodeArchiveSource(archive).read()
    with pytest.raises(SourceFormatError):
        next(reader)
    assert next(reader).conversation.document_id == "claude-code:session-one"


def test_selected_symlink_finishes_with_one_failure(configured, monkeypatch):  # noqa: F811
    from pathlib import Path

    root, _ = configured
    path = synth.write(root / "one.jsonl", synth.debugging())
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p == path or original(p))
    data = invoke(["--source", "claude-code", "--export", str(path)], 1)
    assert data["failed"] == 1 and len(data["outcomes"]) == 1


def test_handoff_from_imported_claude_session(configured, monkeypatch):  # noqa: F811
    from typer.testing import CliRunner

    from engineering_memory.access.synthesis import OpenAICompatibleSynthesizer
    from engineering_memory.cli import app

    root, _ = configured
    records = synth.debugging()
    records[0]["repository"] = "https://example.test/org/orchard.git"
    records[0]["message"]["content"] = "Investigate the relay failure."
    records[3]["message"]["content"][0]["input"]["file_path"] = "relay.conf"
    records.extend(
        [
            synth.record(content="Use port 8123. Should we document the upgrade?"),
            synth.record(
                "assistant",
                [
                    {
                        "type": "tool_use",
                        "id": "call-4",
                        "name": "Bash",
                        "input": {"command": "relay --check"},
                    },
                    {
                        "type": "tool_use",
                        "id": "call-5",
                        "name": "Edit",
                        "input": {"file_path": "proposed.conf"},
                    },
                ],
            ),
            synth.record(
                content=[
                    {
                        "type": "tool_result",
                        "tool_use_id": "call-3",
                        "content": "Updated relay.conf",
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "call-4",
                        "content": "relay check passed",
                    },
                ]
            ),
        ]
    )
    for index, record in enumerate(records):
        record["uuid"] = f"handoff-turn-{index}"
    path = synth.write(root / "handoff.jsonl", records)
    foreign = synth.write(root / "foreign.jsonl", synth.debugging("foreign"))
    for source in (path, foreign):
        assert invoke(["--source", "claude-code", "--export", str(source)])["imported"] == 1

    def summarize(self, passages, times):
        assert passages.keys() == times.keys()
        assert "synthetic-secret-123" not in str(passages)
        assert any("password=" in text for text in passages.values())

        def entry(section, status, text, evidence):
            selector = next(key for key, passage in passages.items() if evidence in passage)
            return {"section": section, "status": status, "text": text, "selectors": [selector]}

        return {
            "entries": [
                entry(
                    "goal", "recorded", "Investigate the relay failure.", "Investigate the relay"
                ),
                entry("decisions", "recorded", "Use port 8123.", "Use port 8123"),
                entry("files", "recorded", "Updated relay.conf.", "Updated relay.conf"),
                entry("checks", "recorded", "Initial relay check failed.", "port zero is disabled"),
                entry("checks", "recorded", "Relay check rerun passed.", "relay check passed"),
                entry(
                    "files",
                    "unknown",
                    "proposed.conf edit has no recorded result.",
                    "proposed.conf",
                ),
                entry(
                    "questions",
                    "unknown",
                    "Should we document the upgrade?",
                    "document the upgrade",
                ),
            ]
        }

    monkeypatch.delenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL")
    monkeypatch.setenv("ENGINEERING_MEMORY_DEEP_RECALL__BASE_URL", "http://proxy")
    monkeypatch.setenv("ENGINEERING_MEMORY_DEEP_RECALL__MODEL", "fixture-model")
    monkeypatch.setattr(OpenAICompatibleSynthesizer, "synthesize_handoff", summarize)
    result = CliRunner().invoke(
        app, ["session-handoff", "claude-code:session-one", "--project", "orchard"]
    )
    assert result.exit_code == 0, (result.output, result.exception)
    assert len(result.stdout.encode()) <= 8 * 1024
    assert "Recorded** — Updated relay.conf." in result.stdout
    assert "Unknown** — proposed.conf edit has no recorded result." in result.stdout
    assert "Initial relay check failed." in result.stdout
    assert "Relay check rerun passed." in result.stdout
    assert result.stdout.count("document=claude-code%3Asession-one") == 7
    assert result.stdout.count("field=tool_result") == 3
    (root / "handoff.md").write_text(result.stdout, encoding="utf-8")
