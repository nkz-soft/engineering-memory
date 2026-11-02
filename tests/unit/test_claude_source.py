"""Claude source dialect, packaging and resource behavior."""

import json
import zipfile
from datetime import UTC, datetime

import pytest

from engineering_memory.ingestion.claude_chat import ClaudeChatExportSource
from engineering_memory.ingestion.source import SourceFormatError
from engineering_memory.normalization import Source
from tests.synthetic import claude_export as synth


def read(tmp_path, values):
    return ClaudeChatExportSource(synth.write(tmp_path / "conversations.json", values)).read()


def test_mapping_and_exact_original(tmp_path):
    value = synth.record()
    value["chat_messages"] += [
        {
            "sender": "assistant",
            "text": "fallback",
            "content": [
                {"type": "text", "text": "Привет\n"},
                {"type": "image"},
                {"type": "text", "text": "world"},
            ],
            "attachments": [{"file_name": "safe.txt"}],
        }
    ]
    raw = json.dumps(value, ensure_ascii=False, indent=2)
    path = tmp_path / "conversations.json"
    path.write_bytes(("[" + raw + "]").encode())
    item = next(ClaudeChatExportSource(path).read())
    assert item.original.content == raw.encode()
    assert item.conversation.source == Source.CLAUDE_CHAT
    assert item.conversation.document_id == "claude-chat:one"
    assert item.conversation.started_at == datetime(2020, 1, 2, tzinfo=UTC)
    assert item.conversation.messages[1].text == "Привет\n\nworld"
    assert [p.kind.value for p in item.conversation.messages[1].non_text_parts] == ["image", "file"]
    assert item.conversation.messages[1].sent_at is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("uuid", ""),
        ("uuid", 1),
        ("created_at", None),
        ("created_at", "2020-01-02"),
        ("chat_messages", None),
        ("chat_messages", [{}]),
        ("chat_messages", [{"sender": "unknown", "text": "PRIVATE"}]),
        ("chat_messages", [{"sender": "human", "content": "PRIVATE"}]),
        ("chat_messages", [{"sender": "human", "content": [{"type": "text", "text": 7}]}]),
    ],
)
def test_bad_record_does_not_stop_reader_or_leak(tmp_path, field, value):
    bad = synth.record("bad")
    bad[field] = value
    reader = read(tmp_path, [bad, synth.record("good")])
    with pytest.raises(SourceFormatError) as raised:
        next(reader)
    assert "PRIVATE" not in str(raised.value)
    assert next(reader).conversation.source_id == "good"
    with pytest.raises(StopIteration):
        next(reader)


def test_duplicate_and_order(tmp_path):
    reader = read(tmp_path, [synth.record("a"), synth.record("a"), synth.record("b")])
    assert next(reader).conversation.source_id == "a"
    with pytest.raises(SourceFormatError):
        next(reader)
    assert next(reader).conversation.source_id == "b"
    reader.close()
    assert list(reader) == []


@pytest.mark.parametrize("package", ["directory", "zip", "json"])
def test_packaging(tmp_path, package):
    path = synth.write(tmp_path / "conversations.json", [synth.record()])
    if package == "directory":
        path = tmp_path
    if package == "zip":
        path = tmp_path / "export.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("conversations.json", json.dumps([synth.record()]))
    reader = ClaudeChatExportSource(path).read()
    assert next(reader).conversation.source_id == "one"
    reader.close()
    if package == "zip":
        path.unlink()  # Windows refuses this if resources remain open.


def test_bad_framing_is_terminal(tmp_path):
    path = tmp_path / "conversations.json"
    path.write_text('[{"uuid": "broken"}', encoding="utf-8")
    reader = ClaudeChatExportSource(path).read()
    with pytest.raises(SourceFormatError):
        next(reader)
    with pytest.raises(SourceFormatError):
        next(reader)
    assert list(reader) == []


def test_rejects_ambiguous_zip(tmp_path):
    path = tmp_path / "export.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("conversations.json", "[]")
        archive.writestr("conversations-000.json", "[]")
    with pytest.raises(SourceFormatError):
        list(ClaudeChatExportSource(path).read())


def test_duplicate_zip_members_refused_and_closed(tmp_path):
    path = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("conversations.json", "[]")
        with pytest.warns(UserWarning):
            archive.writestr("conversations.json", "[]")
    with pytest.raises(SourceFormatError):
        list(ClaudeChatExportSource(path).read())
    path.unlink()


def test_incremental_read_and_cleanup(tmp_path, monkeypatch):
    import io

    from engineering_memory.ingestion.chatgpt.records import RecordScanner
    from engineering_memory.ingestion.claude_chat import source as module

    payload = (
        "["
        + json.dumps(synth.record("first"))
        + ","
        + json.dumps(synth.record("large", "x" * 200_000))
        + "]"
    )
    stream = io.StringIO(payload)

    class Export:
        names = ("conversations.json",)

        def __init__(self, path):
            pass

        def open(self, name):
            return stream

        def close(self):
            pass

    monkeypatch.setattr(module, "Export", Export)
    monkeypatch.setattr(module, "RecordScanner", lambda value: RecordScanner(value, chunk_size=512))
    reader = ClaudeChatExportSource(tmp_path / "conversations.json").read()
    assert next(reader).conversation.source_id == "first"
    assert stream.tell() < len(payload)
    reader.close()
    assert stream.closed


def test_timestamp_overflow_is_record_failure_with_identity(tmp_path):
    value = synth.record("bad-time")
    value["created_at"] = "0001-01-01T00:00:00+01:00"
    reader = read(tmp_path, [value, synth.record("next")])
    with pytest.raises(SourceFormatError) as raised:
        next(reader)
    assert raised.value.subject == "bad-time"
    assert next(reader).conversation.source_id == "next"


def test_duplicate_failure_identifies_record(tmp_path):
    reader = read(tmp_path, [synth.record("same"), synth.record("same")])
    next(reader)
    with pytest.raises(SourceFormatError) as raised:
        next(reader)
    assert raised.value.subject == "same"
