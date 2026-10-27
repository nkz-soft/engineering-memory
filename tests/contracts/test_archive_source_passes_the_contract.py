"""The archive replay source against the shared conversation-source behaviors."""

import pytest

from engineering_memory.archive import ArchiveUnavailable, OriginalPayload
from engineering_memory.ingestion.chatgpt.archive_source import ChatGPTArchiveSource
from tests.contracts import conversations as samples
from tests.contracts.source import ConversationSourceContract
from tests.fakes.archive import InMemoryRawArchive
from tests.synthetic import chatgpt_export as synth


class TestChatGPTArchiveSource(ConversationSourceContract):
    def make_source(self, conversations):
        archive = InMemoryRawArchive()
        for item in conversations:
            archive.store(
                samples.enrich(item),
                OriginalPayload(
                    content=synth.serialize(synth.from_conversation(item)).encode(),
                    media_type="application/json",
                ),
            )
        return ChatGPTArchiveSource(archive)

    def make_source_with_one_unreadable(self, conversations):
        archive = InMemoryRawArchive()
        for index, item in enumerate(conversations):
            archive.store(
                samples.enrich(item),
                OriginalPayload(
                    content=b"{unreadable"
                    if index == 1
                    else synth.serialize(synth.from_conversation(item)).encode(),
                    media_type="application/json",
                ),
            )
        return ChatGPTArchiveSource(archive)

    def make_unreachable_source(self):
        return ChatGPTArchiveSource(InMemoryRawArchive(unavailable=True))

    def test_cs6_an_unreachable_export_is_a_retryable_failure(self):
        # Replay retains the archive error's boundary rather than pretending there is an export.
        with pytest.raises(ArchiveUnavailable) as raised:
            list(self.make_unreachable_source().read())
        assert raised.value.retryable
