"""Streaming export reader; a bad record advances without closing iteration."""

from collections.abc import Iterator
from pathlib import Path

from engineering_memory.archive.interface import OriginalPayload
from engineering_memory.ingestion.chatgpt.records import RecordScanner
from engineering_memory.ingestion.claude_chat.export import Export
from engineering_memory.ingestion.claude_chat.parser import parse_record
from engineering_memory.ingestion.source import SourceConversation, SourceFormatError
from engineering_memory.normalization import Source


class ClaudeChatExportSource:
    source = Source.CLAUDE_CHAT

    def __init__(self, path: Path):
        self._path = Path(path)

    def read(self) -> Iterator[SourceConversation]:
        return _Reader(self._path)


class _Reader(Iterator[SourceConversation]):
    def __init__(self, path):
        self._path = path
        self._export = None
        self._stream = None
        self._scanner = None
        self._done = False
        self._seen = set()

    def __next__(self):
        if self._done:
            raise StopIteration
        try:
            if self._export is None:
                self._export = Export(self._path)
                self._stream = self._export.open(self._export.names[0])
                self._scanner = RecordScanner(self._stream)
            record = next(self._scanner)
        except BaseException:
            self.close()
            raise
        conversation = parse_record(record.value)
        if conversation.source_id in self._seen:
            raise SourceFormatError(
                "duplicate Claude conversation identifier", subject=conversation.source_id
            )
        self._seen.add(conversation.source_id)
        return SourceConversation(
            conversation=conversation,
            original=OriginalPayload(
                content=record.raw.encode("utf-8"), media_type="application/json"
            ),
        )

    def close(self):
        self._done = True
        if self._stream is not None:
            self._stream.close()
        if self._export is not None:
            self._export.close()

    def __del__(self):
        self.close()
