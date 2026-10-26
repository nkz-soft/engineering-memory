"""Replay ChatGPT records from the raw archive through the current parser.

Original bytes, not saved normalized content, drive a replay after parser or redaction changes.
The caller supplies fresh import state when deliberately reprocessing unchanged source content.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from pydantic import ValidationError

from engineering_memory.archive import RawArchive
from engineering_memory.ingestion.chatgpt.conversation import parse_record
from engineering_memory.ingestion.chatgpt.thread import UnreadableRecord
from engineering_memory.ingestion.source import SourceConversation, SourceFormatError
from engineering_memory.normalization import Source

__all__ = ["ChatGPTArchiveSource"]


class ChatGPTArchiveSource:
    """A source over ChatGPT originals; each read starts fresh archive enumeration."""

    source = Source.CHATGPT

    def __init__(self, archive: RawArchive) -> None:
        self._archive = archive

    def read(self) -> Iterator[SourceConversation]:
        return _Reader(self._archive)


class _Reader(Iterator[SourceConversation]):
    def __init__(self, archive: RawArchive) -> None:
        self._archive = archive
        self._identities: Iterator[str] = iter(())
        self._started = False

    def __next__(self) -> SourceConversation:
        if not self._started:
            self._started = True
            self._identities = self._archive.iter_document_ids(source=Source.CHATGPT)
        document_id = next(self._identities)
        # Archive failures retain their boundary/category. The cursor has already advanced.
        original = self._archive.load_original(document_id)
        try:
            if original.media_type != "application/json":
                raise ValueError("unsupported original media type")
            value = json.loads(original.content.decode("utf-8"))
            parsed = parse_record(value)
            if parsed.conversation.document_id != document_id:
                raise ValueError("original identity does not match its archive key")
            return SourceConversation(conversation=parsed.conversation, original=original)
        except (
            ValueError,
            TypeError,
            ValidationError,
            UnreadableRecord,
            RecursionError,
        ) as failure:
            raise SourceFormatError(
                "the archived ChatGPT original could not be parsed", subject=document_id
            ) from failure
