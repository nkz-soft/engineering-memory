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


@pytest.mark.parametrize("automatic", [False, True], ids=["manual", "automatic"])
def test_desktop_rollout_retains_only_response_evidence(tmp_path, automatic):
    from engineering_memory.ingestion.session_capture import CapturedSessionSource

    rows = synth.desktop_rollout()
    path = synth.write(tmp_path / "desktop.jsonl", rows)
    source = (
        CapturedSessionSource("codex", tmp_path, quiet_seconds=0)
        if automatic
        else CodexSessionSource(path)
    )
    item = next(source.read())
    conversation = item.conversation
    assert item.original.content == synth.encode(rows)
    assert conversation.document_id == "codex:desktop-fixture"
    assert conversation.started_at.isoformat() == "2026-03-04T09:30:00+00:00"
    assert conversation.last_activity_at.isoformat() == "2026-03-04T09:31:00+00:00"
    user, request, response, assistant = conversation.messages
    assert user.text == "Which cable specification did we choose?"
    assert assistant.text == "We chose a shielded cable rated for 60 volts."
    assert request.role == Role.ASSISTANT
    assert response.role == Role.TOOL
    assert request.tool_activity[0].name == response.tool_activity[0].name == "exec"
    assert json.loads(request.tool_activity[0].request)["call_id"] == "call-1"
    assert json.loads(response.tool_activity[0].result)["call_id"] == "call-1"
    clean, _ = PatternSecretSanitizer().sanitize(conversation)
    assert "60 volts" in clean.messages[2].tool_activity[0].result
    assert "fixture-test-secret" not in clean.model_dump_json()
    assert "fixture-world-state" not in clean.model_dump_json()
    assert "fixture-ui-result" not in clean.model_dump_json()


@pytest.mark.parametrize(
    "unsupported", ["envelope", "completion", "unmatched-dialogue", "no-result"]
)
def test_desktop_rollout_rejects_unsupported_evidence(tmp_path, unsupported):
    rows = synth.desktop_rollout()
    if unsupported == "envelope":
        rows.append(synth.record("unsupported_record"))
    elif unsupported == "completion":
        rows.append(synth.record("event_msg", type="item_completed", item={"type": "Plan"}))
    elif unsupported == "unmatched-dialogue":
        rows[-2]["payload"]["item"]["content"][0]["text"] = "Event-only answer."
    else:
        rows.pop(8)
    with pytest.raises(SourceFormatError, match="could not be parsed"):
        load(tmp_path, rows)


def test_tool_declaration_after_dialogue_does_not_extend_activity(tmp_path):
    rows = synth.desktop_rollout()
    declaration = rows.pop(1)
    declaration["timestamp"] = "2026-03-05T09:31:00Z"
    rows.append(declaration)
    assert load(tmp_path, rows).conversation.last_activity_at.isoformat() == (
        "2026-03-04T09:31:00+00:00"
    )


@pytest.mark.parametrize("completion_index", [5, 7, 10], ids=["user", "command", "assistant"])
def test_completion_requires_response_evidence_in_its_turn(tmp_path, completion_index):
    rows = synth.desktop_rollout()
    completion = rows[completion_index]
    later = synth.record(
        "event_msg",
        type="item_completed",
        turn_id="later",
        item={**completion["payload"]["item"], "id": "later-item"},
    )
    rows.insert(1, synth.record("event_msg", type="task_started", turn_id="first"))
    rows.extend(
        [
            synth.record("event_msg", type="task_complete", turn_id="first"),
            synth.record("event_msg", type="task_started", turn_id="later"),
            later,
            synth.record("event_msg", type="task_complete", turn_id="later"),
        ]
    )
    with pytest.raises(SourceFormatError):
        load(tmp_path, rows)


def test_distinct_completions_cannot_reuse_one_response_message(tmp_path):
    rows = synth.desktop_rollout()
    original = rows[5]["payload"]["item"]
    second = synth.record("event_msg", type="item_completed", item={**original, "id": "second"})
    rows.insert(6, second)
    with pytest.raises(SourceFormatError):
        load(tmp_path, rows)
