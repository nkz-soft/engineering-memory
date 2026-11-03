"""Codex evidence, identity, safety and bounded compatibility."""

import json

import pytest

from engineering_memory.ingestion.codex import CodexSessionSource
from engineering_memory.ingestion.source import SourceFormatError
from engineering_memory.normalization import Role
from engineering_memory.sanitization import PatternSecretSanitizer
from tests.synthetic import codex as synth


def load(tmp_path, rows):
    return next(CodexSessionSource(synth.write(tmp_path / "one.jsonl", rows)).read())


def test_evidence_order_identity_and_sanitization(tmp_path):
    rows = synth.debugging()
    item = load(tmp_path, rows)
    c = item.conversation
    assert item.original.content == synth.encode(rows)
    assert c.document_id == "codex:session-one"
    assert c.working_directory == "/work/orchard"
    assert [m.role for m in c.messages] == [
        Role.USER,
        Role.ASSISTANT,
        Role.TOOL,
        Role.ASSISTANT,
        Role.ASSISTANT,
    ]
    assert c.messages[0].text == "Why does the relay fail?"
    assert c.messages[2].tool_activity[0].name == "exec_command"
    assert json.loads(c.messages[2].tool_activity[0].result)["call_id"] == "call-1"
    assert c.messages[3].tool_activity[0].result is None
    clean, _ = PatternSecretSanitizer().sanitize(c)
    assert "synthetic-secret-123" not in clean.model_dump_json()
    rows[4]["payload"]["output"] = "different failure"
    assert load(tmp_path, rows).conversation.content_hash() != c.content_hash()


@pytest.mark.parametrize(
    "mutation", ["id", "time", "json", "unknown", "call", "role", "content", "conflict"]
)
def test_invalid_advances_without_leaking(tmp_path, mutation):
    rows = synth.debugging()
    if mutation == "id":
        rows[0]["payload"]["id"] = ""
    if mutation == "time":
        rows[1]["timestamp"] = "2026-03-04"
    if mutation == "unknown":
        rows[1]["payload"]["type"] = "new_private_content"
    if mutation == "call":
        rows[3]["payload"]["call_id"] = None
    if mutation == "role":
        rows[1]["payload"]["role"] = "invented"
    if mutation == "content":
        rows[1]["payload"]["content"][0]["text"] = 42
    if mutation == "conflict":
        rows.append(synth.record("session_meta", id="other", timestamp=synth.TIME))
    raw = synth.encode(rows) + (b'{"PRIVATE"' if mutation == "json" else b"")
    (tmp_path / "a.jsonl").write_bytes(raw)
    synth.write(tmp_path / "b.jsonl", synth.debugging())
    reader = CodexSessionSource(tmp_path).read()
    with pytest.raises(SourceFormatError) as error:
        next(reader)
    assert "PRIVATE" not in str(error.value)
    assert next(reader).conversation.source_id == "session-one"


def test_metadata_only_and_event_only(tmp_path):
    assert load(tmp_path, synth.debugging()[:1]).conversation.messages == ()
    with pytest.raises(SourceFormatError):
        load(
            tmp_path,
            [
                *synth.debugging()[:1],
                synth.record("event_msg", type="user_message", message="lost"),
            ],
        )


def test_orphan_output_nontext_and_compaction(tmp_path):
    rows = [
        *synth.debugging()[:1],
        synth.record(
            "response_item", type="custom_tool_call_output", call_id="missing", output="failed"
        ),
        synth.record(
            "response_item",
            type="message",
            role="developer",
            content=[{"type": "input_image", "image_url": "PRIVATE"}],
        ),
        synth.record("compacted", message="duplicate", replacement_history=[]),
    ]
    c = load(tmp_path, rows).conversation
    assert c.messages[0].tool_activity[0].name == "unknown-tool"
    assert c.messages[1].role == Role.SYSTEM
    assert c.messages[1].non_text_parts
    assert "PRIVATE" not in c.model_dump_json()


def test_duplicate_sessions_and_empty_directory(tmp_path):
    assert list(CodexSessionSource(tmp_path).read()) == []
    synth.write(tmp_path / "a.jsonl", synth.debugging())
    synth.write(tmp_path / "b.jsonl", synth.debugging())
    reader = CodexSessionSource(tmp_path).read()
    next(reader)
    with pytest.raises(SourceFormatError):
        next(reader)
    with pytest.raises(StopIteration):
        next(reader)


def test_nested_multiline_secrets(tmp_path):
    rows = synth.debugging()
    secret = "-----BEGIN PRIVATE KEY-----\nSYNTHETICMULTILINE\n-----END PRIVATE KEY-----"
    rows[3]["payload"]["arguments"] = json.dumps({"nested": {"value": secret}})
    rows[4]["payload"]["output"] = json.dumps({"value": secret})
    clean, _ = PatternSecretSanitizer().sanitize(load(tmp_path, rows).conversation)
    assert "SYNTHETICMULTILINE" not in clean.model_dump_json()


def test_unknown_event_fails_instead_of_importing_empty(tmp_path):
    rows = [*synth.debugging()[:1], synth.record("event_msg", type="new_content", text="lost")]
    with pytest.raises(SourceFormatError):
        load(tmp_path, rows)


def test_output_arrays_preserve_text_and_nontext_presence(tmp_path):
    rows = synth.debugging()
    rows[4]["payload"]["output"] = [
        {"type": "input_text", "text": "failed port zero"},
        {"type": "input_image", "image_url": "PRIVATE"},
    ]
    c = load(tmp_path, rows).conversation
    assert "failed port zero" in c.messages[2].tool_activity[0].result
    assert c.messages[2].non_text_parts
    assert "PRIVATE" not in c.model_dump_json()


def test_directory_symlink_reports_one_failure_and_continues(tmp_path, monkeypatch):
    from pathlib import Path

    path = synth.write(tmp_path / "a.jsonl", synth.debugging())
    synth.write(tmp_path / "b.jsonl", synth.debugging("other"))
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p == path or original(p))
    reader = CodexSessionSource(tmp_path).read()
    with pytest.raises(SourceFormatError):
        next(reader)
    assert next(reader).conversation.source_id == "other"
