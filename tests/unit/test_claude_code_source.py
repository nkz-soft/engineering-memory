"""Claude Code normalization must keep the evidence and isolate malformed sessions."""

import json
from datetime import UTC, datetime

import pytest

from engineering_memory.ingestion.source import SourceFormatError, SourceUnavailable
from engineering_memory.normalization import Role
from engineering_memory.sanitization import PatternSecretSanitizer
from tests.synthetic import claude_code as synth


def source(path):
    from engineering_memory.ingestion.claude_code import ClaudeCodeSessionSource

    return ClaudeCodeSessionSource(path)


def test_order_tools_original_and_hash(tmp_path):
    path = synth.write(tmp_path / "one.jsonl", synth.debugging())
    item = next(source(path).read())
    c = item.conversation
    assert item.original.content == path.read_bytes()
    assert item.original.media_type == "application/x-ndjson"
    assert c.document_id == "claude-code:session-one"
    assert c.started_at == datetime(2026, 3, 4, 9, 30, tzinfo=UTC)
    assert c.working_directory == "/work/orchard"
    assert [m.role for m in c.messages] == [
        Role.USER,
        Role.ASSISTANT,
        Role.ASSISTANT,
        Role.ASSISTANT,
        Role.TOOL,
        Role.TOOL,
        Role.ASSISTANT,
        Role.ASSISTANT,
    ]
    assert [c.messages[i].tool_activity[0].name for i in (2, 3, 4, 5)] == [
        "Bash",
        "Read",
        "Read",
        "Bash",
    ]
    result = json.loads(c.messages[5].tool_activity[0].result)
    assert result["tool_use_id"] == "call-1" and result["is_error"] is True
    assert "port zero" in result["content"]
    assert c.messages[6].tool_activity[0].result is None
    clean, _ = PatternSecretSanitizer().sanitize(c)
    assert "synthetic-secret-123" not in clean.model_dump_json()
    records = synth.debugging()
    records[2]["message"]["content"][1]["content"] = "different error"
    synth.write(path, records)
    assert next(source(path).read()).conversation.content_hash() != c.content_hash()


@pytest.mark.parametrize(
    "field,value",
    [
        ("sessionId", ""),
        ("sessionId", 3),
        ("uuid", ""),
        ("timestamp", "2026-03-04"),
        ("message", {}),
        ("message", {"content": [{"type": "text", "text": 7}]}),
        ("message", {"content": [{"type": "tool_use", "id": "x", "name": "Bash"}]}),
        ("message", {"content": [{"type": "tool_result", "tool_use_id": "x", "is_error": "yes"}]}),
    ],
)
def test_bad_session_advances_without_payload_in_error(tmp_path, field, value):
    bad = synth.record(content="PRIVATE")
    bad[field] = value
    synth.write(tmp_path / "a.jsonl", [bad])
    synth.write(tmp_path / "b.jsonl", [synth.record()])
    reader = source(tmp_path).read()
    with pytest.raises(SourceFormatError) as caught:
        next(reader)
    assert "PRIVATE" not in str(caught.value)
    assert next(reader).conversation.source_id == "session-one"


@pytest.mark.parametrize("kind", ["duplicate", "conflict", "json", "surrogate"])
def test_refuses_ambiguous_or_incomplete_session(tmp_path, kind):
    records = synth.debugging()
    if kind == "duplicate":
        records[1]["uuid"] = records[0]["uuid"]
    if kind == "conflict":
        records[1]["sessionId"] = "other"
    if kind == "surrogate":
        records[1]["message"]["content"][0]["text"] = "\ud800"
        raw = (json.dumps(records[1]) + "\n").encode()
    else:
        raw = synth.encode(records) + (b'{"PRIVATE"' if kind == "json" else b"")
    path = tmp_path / "one.jsonl"
    path.write_bytes(raw)
    with pytest.raises(SourceFormatError):
        next(source(path).read())


def test_orphan_nested_nontext_sidechain_and_metadata(tmp_path):
    records = [
        {"type": "progress"},
        synth.record(
            content=[
                {
                    "type": "tool_result",
                    "tool_use_id": "orphan",
                    "content": [
                        {"type": "text", "text": "first"},
                        {"type": "image"},
                        {"type": "text", "text": "second"},
                    ],
                }
            ]
        ),
        dict(synth.record(content="SIDECHAIN PRIVATE"), uuid="side", isSidechain=True),
        dict(
            synth.record("assistant", [{"type": "thinking", "thinking": "PRIVATE"}]),
            uuid="thinking",
        ),
    ]
    c = next(source(synth.write(tmp_path / "s.jsonl", records)).read()).conversation
    assert c.messages[0].tool_activity[0].name == "unknown-tool"
    assert json.loads(c.messages[0].tool_activity[0].result)["content"] == "first\nsecond"
    assert c.messages[0].non_text_parts
    assert "PRIVATE" not in c.model_dump_json()
    assert len(c.messages) == 3


def test_empty_metadata_only_and_unreachable(tmp_path):
    synth.write(tmp_path / "empty.jsonl", [])
    synth.write(tmp_path / "metadata.jsonl", [{"type": "progress"}])
    assert list(source(tmp_path).read()) == []
    with pytest.raises(SourceUnavailable):
        next(source(tmp_path / "absent").read())


def test_first_context_and_duplicate_session_files(tmp_path):
    records = synth.debugging()
    records[0]["repository"] = "https://example.test/org/orchard.git"
    records[1]["cwd"] = "/work/elsewhere"
    synth.write(tmp_path / "a.jsonl", records)
    synth.write(tmp_path / "b.jsonl", records)
    reader = source(tmp_path).read()
    c = next(reader).conversation
    assert c.repository == "https://example.test/org/orchard.git"
    assert c.working_directory == "/work/orchard"
    with pytest.raises(SourceFormatError):
        next(reader)


def test_snapshot_discovery_does_not_read_nested_or_external_files(tmp_path):
    synth.write(tmp_path / "main.jsonl", synth.debugging())
    synth.write(tmp_path / "subagents" / "agent.jsonl", [{"PRIVATE": "not a session"}])
    external = tmp_path / "external.txt"
    external.write_text("PRIVATE external output")
    records = synth.debugging()
    records[2]["message"]["content"][0]["content"] = [
        {"type": "text", "text": "available output"},
        {"type": "document", "source": {"path": str(external)}},
    ]
    synth.write(tmp_path / "main.jsonl", records)
    items = list(source(tmp_path).read())
    assert len(items) == 1
    assert "PRIVATE external output" not in items[0].conversation.model_dump_json()
    assert items[0].conversation.messages[4].non_text_parts


def test_rejected_input_symlink_is_consumed_once(tmp_path, monkeypatch):
    from pathlib import Path

    path = synth.write(tmp_path / "one.jsonl", synth.debugging())
    monkeypatch.setattr(Path, "is_symlink", lambda _: True)
    reader = source(path).read()
    with pytest.raises(SourceFormatError):
        next(reader)
    with pytest.raises(StopIteration):
        next(reader)


@pytest.mark.parametrize("location", ["request", "result"])
def test_multiline_private_key_in_tool_json_is_redacted(tmp_path, location):
    from engineering_memory.sanitization import RedactionCategory
    from tests.synthetic.secrets import SAMPLES

    secret = next(
        sample.sentence for sample in SAMPLES if sample.category == RedactionCategory.PRIVATE_KEY
    )
    records = synth.debugging()
    if location == "request":
        records[3]["message"]["content"][0]["input"]["new_string"] = secret
    else:
        records[2]["message"]["content"][1]["content"] = "error before\n" + secret + "\nafter"
    path = synth.write(tmp_path / "session.jsonl", records)
    c = next(source(path).read()).conversation
    clean, report = PatternSecretSanitizer().sanitize(c)
    texts = [a.request or a.result for m in clean.messages for a in m.tool_activity]
    assert all(
        secret not in json.dumps(json.loads(text), ensure_ascii=False)
        and secret not in str(json.loads(text))
        for text in texts
    )
    assert all(secret.splitlines()[2] not in text for text in texts)
    assert report.counts[RedactionCategory.PRIVATE_KEY] == 1


def test_jsonl_preserves_unicode_line_separators_in_text(tmp_path):
    records = [synth.record(content="Привет\u2028world")]
    path = synth.write(tmp_path / "one.jsonl", records)
    assert next(source(path).read()).conversation.messages[0].text == "Привет\u2028world"
