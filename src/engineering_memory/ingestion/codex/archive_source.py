"""Replay exact archived session bytes through the current parser."""

from collections.abc import Iterator

from engineering_memory.archive import RawArchive
from engineering_memory.ingestion.codex.parser import parse_session
from engineering_memory.ingestion.source import SourceConversation, SourceFormatError
from engineering_memory.normalization import Source


class CodexArchiveSource:
    source = Source.CODEX

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
            self._identities = iter(self._archive.iter_document_ids(source=Source.CODEX))
        document_id = next(self._identities)
        original = self._archive.load_original(document_id)
        try:
            if original.media_type != "application/x-ndjson":
                raise ValueError
            conversation = parse_session(original.content)
            if conversation is None or conversation.document_id != document_id:
                raise ValueError
        except (ValueError, SourceFormatError):
            raise SourceFormatError(
                "the archived Codex original could not be parsed", subject=document_id
            ) from None
        return SourceConversation(conversation=conversation, original=original)
