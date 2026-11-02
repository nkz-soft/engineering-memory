"""Replay Claude originals through the current parser, never normalized snapshots."""

import json
from collections.abc import Iterator

from engineering_memory.archive import RawArchive
from engineering_memory.ingestion.claude_chat.parser import parse_record
from engineering_memory.ingestion.source import SourceConversation, SourceFormatError
from engineering_memory.normalization import Source


class ClaudeChatArchiveSource:
    source = Source.CLAUDE_CHAT

    def __init__(self, archive: RawArchive):
        self._archive = archive

    def read(self) -> Iterator[SourceConversation]:
        return _Reader(self._archive)


class _Reader(Iterator[SourceConversation]):
    def __init__(self, archive):
        self._archive = archive
        self._identities = None

    def __next__(self):
        if self._identities is None:
            self._identities = iter(self._archive.iter_document_ids(source=Source.CLAUDE_CHAT))
        document_id = next(self._identities)
        original = self._archive.load_original(document_id)
        try:
            if original.media_type != "application/json":
                raise ValueError
            conversation = parse_record(json.loads(original.content.decode("utf-8")))
            if conversation.document_id != document_id:
                raise ValueError
        except (ValueError, TypeError, RecursionError, SourceFormatError):
            raise SourceFormatError(
                "the archived Claude original could not be parsed", subject=document_id
            ) from None
        return SourceConversation(conversation=conversation, original=original)
