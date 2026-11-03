"""Real CLI/archive/state composition for Codex history."""

import json

import pytest

from engineering_memory.access.service import MemoryAccess
from engineering_memory.archive.local import LocalRawArchive
from tests.integration.test_claude_cli import configured, invoke  # noqa: F401
from tests.synthetic import codex as synth


def test_import_evidence_provenance_skip_update_and_archive_replay(configured):  # noqa: F811
    root, memory = configured
    records = synth.debugging()
    records[0]["payload"]["git"] = {"repository_url": "https://example.test/org/orchard.git"}
    path = synth.write(root / "one.jsonl", records)
    args = ["--source", "codex", "--export", str(path)]
    assert invoke(args)["imported"] == 1
    archive = LocalRawArchive(root / "archive")
    saved = archive.load("codex:session-one")
    assert saved.provenance.project == "orchard"
    assert saved.provenance.repository == "https://example.test/org/orchard.git"
    assert {str(t) for t in saved.tags} >= {"source:codex", "project:orchard"}
    assert invoke(args)["skipped"] == 1
    access = MemoryAccess(memory, archive)
    found = access.search_memory(query="relay", tags=["source:codex", "project:orchard"])
    assert found["results"][0]["document_id"] == "codex:session-one"
    assert not access.search_memory(query="relay", tags=["source:claude-code"])["results"]
    opened = json.dumps(access.get_conversation(document_id="codex:session-one"))
    assert "port zero" in opened and "new_string" in opened
    assert "synthetic-secret-123" not in opened
    assert b"synthetic-secret-123" in archive.load_original("codex:session-one").content
    records[4]["payload"]["output"] = "Updated failure"
    synth.write(path, records)
    assert invoke(args)["imported"] == 1
    path.unlink()
    assert invoke(["--source", "codex", "--from-archive", "--force"])["imported"] == 1
    assert len(memory.retained) == 1
    assert "Updated failure" in archive.load("codex:session-one").model_dump_json()
    assert invoke(["--source", "codex", "--from-archive"])["skipped"] == 1


def test_preview_no_writes_or_memory_construction(configured, monkeypatch):  # noqa: F811
    root, _ = configured
    monkeypatch.setattr(
        "engineering_memory.cli.runtime.make_memory",
        lambda _: pytest.fail("dry-run constructed memory"),
    )
    path = synth.write(root / "one.jsonl", synth.debugging())
    data = invoke(["--source", "codex", "--export", str(path), "--dry-run"])
    assert data["would_import"] == 1
    assert not (root / "state.db").exists()
    assert not (root / "archive").exists()


def test_bad_file_does_not_abort_batch(configured):  # noqa: F811
    root, _ = configured
    folder = root / "sessions"
    synth.write(folder / "a.jsonl", [{"type": "user", "PRIVATE": "PRIVATE"}])
    synth.write(folder / "b.jsonl", synth.debugging())
    data = invoke(["--source", "codex", "--export", str(folder)], 1)
    assert (data["imported"], data["failed"]) == (1, 1)
    assert "PRIVATE" not in json.dumps(data)


def test_each_session_has_own_sanitized_repository(configured):  # noqa: F811
    root, _ = configured
    folder = root / "sessions"
    for index, name in enumerate(("orchard", "lantern")):
        records = synth.debugging(f"session-{index}")
        records[0]["payload"]["git"] = {
            "repository_url": f"https://example.test/{name}.git password=" + "synthetic-secret-123"
        }
        synth.write(folder / f"{index}.jsonl", records)
    assert invoke(["--source", "codex", "--export", str(folder)])["imported"] == 2
    archive = LocalRawArchive(root / "archive")
    for index, name in enumerate(("orchard", "lantern")):
        saved = archive.load(f"codex:session-{index}")
        assert name in saved.provenance.repository
        assert "synthetic-secret-123" not in saved.model_dump_json()


def test_archive_refuses_wrong_identity_and_advances(configured):  # noqa: F811
    from unittest.mock import Mock

    from engineering_memory.archive import OriginalPayload
    from engineering_memory.ingestion.codex.archive_source import CodexArchiveSource
    from engineering_memory.ingestion.source import SourceFormatError

    archive = Mock()
    archive.iter_document_ids.return_value = iter(["codex:wrong", "codex:session-one"])
    archive.load_original.return_value = OriginalPayload(
        content=synth.encode(synth.debugging()), media_type="application/x-ndjson"
    )
    reader = CodexArchiveSource(archive).read()
    with pytest.raises(SourceFormatError):
        next(reader)
    assert next(reader).conversation.document_id == "codex:session-one"


def test_selected_symlink_finishes_with_one_failure(configured, monkeypatch):  # noqa: F811
    from pathlib import Path

    root, _ = configured
    path = synth.write(root / "one.jsonl", synth.debugging())
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p == path or original(p))
    data = invoke(["--source", "codex", "--export", str(path)], 1)
    assert data["failed"] == 1 and len(data["outcomes"]) == 1


def test_windows_metadata_precedes_prose_and_valid_bad_valid_recovers(configured):  # noqa: F811
    root, _ = configured
    folder = root / "sessions"
    for filename, identity, cwd in (
        ("a", "one", r"D:\work\orchard"),
        ("c", "two", "/work/lantern"),
    ):
        rows = synth.debugging(identity)
        rows[0]["payload"]["cwd"] = cwd
        rows[1]["payload"]["content"][0]["text"] = "orchard mentioned in prose"
        synth.write(folder / f"{filename}.jsonl", rows)
    synth.write(folder / "b.jsonl", [{"PRIVATE": "PRIVATE"}])
    data = invoke(["--source", "codex", "--export", str(folder)], 1)
    assert (data["imported"], data["failed"]) == (2, 1)
    archive = LocalRawArchive(root / "archive")
    assert archive.load("codex:one").provenance.project == "orchard"
    assert archive.load("codex:two").provenance.project == "lantern"
