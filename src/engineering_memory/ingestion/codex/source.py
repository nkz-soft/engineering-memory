"""One snapshot per conversation, with resumable per-file failures."""

from collections.abc import Iterator
from pathlib import Path

from engineering_memory.archive import OriginalPayload
from engineering_memory.ingestion.codex.parser import parse_session
from engineering_memory.ingestion.source import (
    SourceConversation,
    SourceFormatError,
    SourceUnavailable,
)
from engineering_memory.normalization import Source


class CodexSessionSource:
    source = Source.CODEX

    def __init__(self, path: Path):
        self._path = Path(path)

    def read(self) -> Iterator[SourceConversation]:
        return _Reader(self._path)


class _Reader(Iterator[SourceConversation]):
    def __init__(self, path):
        self._path = path
        self._paths = None
        self._seen = set()

    def __next__(self):
        try:
            if self._paths is None:
                if self._path.is_symlink():
                    self._paths = iter(())
                    raise SourceFormatError("session snapshots must not be symlinks")
                if self._path.is_dir():
                    self._paths = iter(
                        sorted(
                            p for p in self._path.glob("*.jsonl") if p.is_symlink() or p.is_file()
                        )
                    )
                elif self._path.is_file():
                    self._paths = iter((self._path,))
                else:
                    raise SourceUnavailable("the Codex snapshot could not be reached")
            while True:
                path = next(self._paths)
                if path.is_symlink():
                    raise SourceFormatError("session snapshots must not be symlinks")
                raw = path.read_bytes()
                conversation = parse_session(raw)
                if conversation is None:
                    continue
                if conversation.source_id in self._seen:
                    raise SourceFormatError("duplicate Codex session identifier")
                self._seen.add(conversation.source_id)
                return SourceConversation(
                    conversation=conversation,
                    original=OriginalPayload(content=raw, media_type="application/x-ndjson"),
                )
        except OSError:
            raise SourceUnavailable("the Codex snapshot could not be reached") from None
