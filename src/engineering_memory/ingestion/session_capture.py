"""Capture stable, bounded local session snapshots for the normal import pipeline."""

import errno
import os
import re
import stat
import time
from collections.abc import Iterator
from pathlib import Path

from engineering_memory.archive import OriginalPayload
from engineering_memory.ingestion.claude_code.parser import parse_session as parse_claude_code
from engineering_memory.ingestion.codex.parser import parse_main_session as parse_codex
from engineering_memory.ingestion.session_paths import RedirectedPath, capture_directory
from engineering_memory.ingestion.source import (
    SourceConversation,
    SourceFormatError,
    SourceUnavailable,
)
from engineering_memory.normalization import Source

_PARSERS = {Source.CODEX: parse_codex, Source.CLAUDE_CODE: parse_claude_code}
_CODEX_LEVELS = (r"[0-9]{4}", r"[0-9]{2}", r"[0-9]{2}")


def _stamp(info: os.stat_result) -> tuple[int, ...]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _snapshot(path: Path, cutoff_ns: int) -> bytes | None:
    with capture_directory(path.parent) as directory:
        before = directory.stat(path.name)
        if not stat.S_ISREG(before.st_mode) or before.st_mtime_ns > cutoff_ns:
            return None
        expected = _stamp(before)
        with directory.open(path.name) as stream:
            opened = _stamp(os.fstat(stream.fileno()))
            # Windows can report different creation/change times for path and handle queries.
            if opened[:-1] != expected[:-1]:
                return None
            raw = stream.read(before.st_size + 1)
            after = os.fstat(stream.fileno())
        if len(raw) != before.st_size or _stamp(after) != opened:
            return None
    with capture_directory(path.parent) as current:
        return raw if _stamp(current.stat(path.name)) == expected else None


def _subdirectory(kind: Source, depth: int, name: str) -> bool:
    if kind == Source.CLAUDE_CODE:
        return depth == 0 and name.casefold() != "subagents"
    return depth < len(_CODEX_LEVELS) and re.fullmatch(_CODEX_LEVELS[depth], name) is not None


def _entries(root: Path, kind: Source, depth: int) -> list[tuple[Path, bool] | None]:
    entries = []
    with capture_directory(root) as directory:
        for entry in sorted(directory.names()):
            name = entry.casefold()
            path = root / entry
            is_snapshot = path.suffix.casefold() == ".jsonl" and (
                (kind == Source.CODEX and depth in {0, len(_CODEX_LEVELS)})
                or (kind == Source.CLAUDE_CODE and not name.startswith("agent-"))
            )
            is_subdirectory = _subdirectory(kind, depth, name)
            if not (is_snapshot or is_subdirectory):
                continue
            try:
                info = directory.stat(entry)
            except (RedirectedPath, FileNotFoundError):
                continue
            except OSError:
                entries.append(None)
                continue
            if is_snapshot and stat.S_ISREG(info.st_mode):
                entries.append((path, False))
            elif is_subdirectory and stat.S_ISDIR(info.st_mode):
                entries.append((path, True))
    return entries


def _candidates(root: Path, kind: Source, depth: int = 0) -> Iterator[Path | None]:
    try:
        entries = _entries(root, kind, depth)
    except (OSError, RedirectedPath):
        if depth == 0:
            raise SourceUnavailable("configured history root could not be reached") from None
        yield None
        return
    for entry in entries:
        if entry is None:
            yield None
        elif entry[1]:
            yield from _candidates(entry[0], kind, depth + 1)
        else:
            yield entry[0]


class CapturedSessionSource:
    """Publish only complete in-memory snapshots through the conversation source interface."""

    def __init__(self, kind: str, root: Path, quiet_seconds: int):
        self.source = Source(kind)
        self._root = root
        self._quiet_seconds = quiet_seconds
        self.deferred = 0

    def read(self) -> Iterator[SourceConversation]:
        self.deferred = 0
        cutoff_ns = time.time_ns() - self._quiet_seconds * 1_000_000_000
        return _CaptureReader(self, _candidates(self._root, self.source), cutoff_ns)


class _CaptureReader(Iterator[SourceConversation]):
    def __init__(
        self, source: CapturedSessionSource, candidates: Iterator[Path | None], cutoff: int
    ):
        self._source = source
        self._candidates = candidates
        self._cutoff = cutoff
        self._seen: set[str] = set()

    def __next__(self) -> SourceConversation:
        for path in self._candidates:
            if path is None:
                raise SourceFormatError("a history entry could not be inspected")
            try:
                raw = _snapshot(path, self._cutoff)
            except (FileNotFoundError, NotADirectoryError, IsADirectoryError, RedirectedPath):
                raw = None
            except OSError as error:
                if error.errno != errno.ELOOP:
                    raise SourceFormatError("a history snapshot could not be read") from None
                raw = None
            if raw is None:
                self._source.deferred += 1
                continue
            conversation = _PARSERS[self._source.source](raw)
            if conversation is None:
                continue
            if conversation.source_id in self._seen:
                raise SourceFormatError("duplicate session identifier")
            self._seen.add(conversation.source_id)
            return SourceConversation(
                conversation=conversation,
                original=OriginalPayload(content=raw, media_type="application/x-ndjson"),
            )
        raise StopIteration
