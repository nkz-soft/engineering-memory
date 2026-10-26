"""Replay must use originals, preserve identities and survive individual failures."""

import importlib.util

import pytest

from engineering_memory.archive import ArchiveUnavailable, OriginalPayload
from engineering_memory.ingestion import SourceFormatError
from engineering_memory.normalization import Source
from tests.contracts import conversations
from tests.fakes.archive import InMemoryRawArchive
from tests.synthetic import chatgpt_export as synth


def replay(archive):
    assert (
        importlib.util.find_spec("engineering_memory.ingestion.chatgpt.archive_source") is not None
    )
    from engineering_memory.ingestion.chatgpt.archive_source import ChatGPTArchiveSource

    return ChatGPTArchiveSource(archive)


def put(archive, item, *, content=None, media_type="application/json"):
    payload = OriginalPayload(
        content=content
        if content is not None
        else synth.serialize(synth.from_conversation(item)).encode(),
        media_type=media_type,
    )
    archive.store(conversations.enrich(item), payload)
    return payload


def test_replay_reparses_original_rather_than_loading_old_normalized_form():
    class OriginalOnlyArchive(InMemoryRawArchive):
        def load(self, document_id):
            raise AssertionError("replay used the old normalized form")

    archive = OriginalOnlyArchive()
    original = conversations.conversation(text="the original answer")
    payload = put(archive, original)
    archive.store(
        conversations.enrich(conversations.conversation(text="old sanitized answer")), payload
    )
    source = replay(archive)
    assert source.source is Source.CHATGPT
    first = list(source.read())
    assert first == list(source.read())
    assert first[0].conversation == original
    assert first[0].original == payload


def test_replay_is_empty_and_filters_other_sources():
    archive = InMemoryRawArchive()
    assert list(replay(archive).read()) == []
    put(archive, conversations.conversation("codex", source=Source.CODEX), content=b"not JSON")
    put(archive, conversations.conversation("chat"))
    assert [one.conversation.source_id for one in replay(archive).read()] == ["chat"]


@pytest.mark.parametrize(
    "content,media_type",
    [
        (b"{private-canary", "application/json"),
        (b"\xff", "application/json"),
        (b"[]", "application/json"),
        (b"{}", "application/json"),
        (b"{}", "text/plain"),
        (None, "identity-mismatch"),
    ],
)
def test_bad_original_reports_safely_and_next_document_is_still_available(content, media_type):
    archive = InMemoryRawArchive()
    bad = conversations.conversation("bad")
    if media_type == "identity-mismatch":
        content = synth.serialize(
            synth.from_conversation(conversations.conversation("other"))
        ).encode()
        media_type = "application/json"
    put(archive, bad, content=content, media_type=media_type)
    put(archive, conversations.conversation("good"))
    reader = replay(archive).read()
    with pytest.raises(SourceFormatError) as raised:
        next(reader)
    assert raised.value.subject == "chatgpt:bad"
    assert "private-canary" not in str(raised.value)
    assert next(reader).conversation.source_id == "good"
    with pytest.raises(StopIteration):
        next(reader)


def test_archive_read_failure_preserves_its_boundary_and_iteration_continues():
    class FailingOriginal(InMemoryRawArchive):
        def load_original(self, document_id):
            if document_id == "chatgpt:bad":
                raise ArchiveUnavailable("archive temporarily unavailable", subject=document_id)
            return super().load_original(document_id)

    archive = FailingOriginal()
    put(archive, conversations.conversation("bad"))
    put(archive, conversations.conversation("good"))
    reader = replay(archive).read()
    with pytest.raises(ArchiveUnavailable):
        next(reader)
    assert next(reader).conversation.source_id == "good"


def test_unavailable_listing_is_reported_once_then_replay_finishes():
    reader = replay(InMemoryRawArchive(unavailable=True)).read()
    with pytest.raises(ArchiveUnavailable):
        next(reader)
    with pytest.raises(StopIteration):
        next(reader)


def test_malformed_message_role_is_a_source_error_and_next_document_survives():
    archive = InMemoryRawArchive()
    bad = conversations.conversation("bad")
    record = synth.from_conversation(bad)
    record["mapping"][record["current_node"]]["message"]["author"]["role"] = []
    put(archive, bad, content=synth.serialize(record).encode())
    put(archive, conversations.conversation("good"))
    reader = replay(archive).read()
    with pytest.raises(SourceFormatError):
        next(reader)
    assert next(reader).conversation.source_id == "good"
