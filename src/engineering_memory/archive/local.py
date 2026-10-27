"""Local paired raw archive, version 1. See specs/012-local-raw-archive/data-model.md.

A complete envelope is the publication unit. One writer and independent readers are supported;
separate load calls need not refer to the same revision while that writer is active.
"""

from __future__ import annotations

import base64
import binascii
import os
import re
import tempfile
from collections.abc import Iterator
from contextlib import suppress
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import ValidationError, field_validator

from engineering_memory.archive.interface import (
    ArchiveDocumentNotFound,
    ArchiveRejected,
    ArchiveUnavailable,
    OriginalPayload,
)
from engineering_memory.normalization import EnrichedConversation, Source
from engineering_memory.normalization.base import FrozenModel, Text


class _Original(FrozenModel):
    media_type: Text
    content_base64: str
    sha256: str


class _Envelope(FrozenModel):
    format_version: Literal[1]
    document_id: str
    enriched: EnrichedConversation
    content_hash: str
    original: _Original

    @field_validator("format_version", mode="before")
    @classmethod
    def _integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("the format version must be an integer")
        return value

    def payload(self) -> OriginalPayload:
        content = base64.b64decode(self.original.content_base64, validate=True)
        if sha256(content).hexdigest() != self.original.sha256:
            raise ValueError("original integrity mismatch")
        return OriginalPayload(content=content, media_type=self.original.media_type)


def _key(document_id: str) -> str:
    return sha256(document_id.encode("utf-8")).hexdigest()


def _redirected(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        # File data is fsynced; publication uses Windows write-through below. Python's fsync
        # cannot sync directory handles on Windows. Do not claim arbitrary power-loss safety.
        return
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _mkdir(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise NotADirectoryError
        return
    _mkdir(path.parent)
    path.mkdir(mode=0o700)
    _sync_directory(path.parent)


def _publish(temporary: Path, destination: Path) -> None:
    if os.name == "nt":
        from engineering_memory.archive._windows import publish

        publish(temporary, destination)
    else:
        os.replace(temporary, destination)
    _sync_directory(destination.parent)


def _read_bytes(path: Path) -> bytes:
    if os.name == "nt":
        from engineering_memory.archive._windows import read_bytes

        return read_bytes(path)
    return path.read_bytes()


class LocalRawArchive:
    """Persist both forms in a local directory; construction performs no IO.

    Pass Settings.archive_root from the composition root. Reading an absent archive is empty.
    The caller sanitizes normalized forms; originals intentionally remain unchanged locally.
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root).absolute()
        self._directory = self._root / "v1"

    def _check_directory(self) -> None:
        if _redirected(self._root) or _redirected(self._directory):
            raise ArchiveRejected("the archive directory is redirected")
        if self._root.exists() and not self._root.is_dir():
            raise ArchiveUnavailable("the archive root is not a directory")
        if self._directory.exists() and not self._directory.is_dir():
            raise ArchiveUnavailable("the archive version path is not a directory")

    def store(self, enriched: EnrichedConversation, original: OriginalPayload) -> None:
        document_id = enriched.document_id
        temporary = None
        try:
            self._check_directory()
            destination = self._directory / (_key(document_id) + ".json")
            if _redirected(destination):
                raise ArchiveRejected("the archive record is redirected", subject=document_id)
            envelope = _Envelope(
                format_version=1,
                document_id=document_id,
                enriched=enriched,
                content_hash=enriched.content_hash(),
                original=_Original(
                    media_type=original.media_type,
                    content_base64=base64.b64encode(original.content).decode("ascii"),
                    sha256=sha256(original.content).hexdigest(),
                ),
            )
            data = envelope.model_dump_json().encode("utf-8")
            _mkdir(self._directory)
            with tempfile.NamedTemporaryFile(
                dir=self._directory, prefix=".", suffix=".tmp", delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            _publish(temporary, destination)
        except OSError as failure:
            raise ArchiveUnavailable(
                "the archive could not persist the record", subject=document_id
            ) from failure
        except (ValueError, ValidationError) as failure:
            raise ArchiveRejected(
                "the archive refused the record", subject=document_id
            ) from failure
        finally:
            if temporary is not None:
                with suppress(OSError):
                    temporary.unlink(missing_ok=True)

    def _read(self, path: Path, document_id: str | None = None) -> _Envelope:
        try:
            self._check_directory()
            if _redirected(path):
                raise ArchiveRejected("the archive record is redirected", subject=document_id)
            if not re.fullmatch(r"[0-9a-f]{64}\.json", path.name):
                raise ArchiveRejected("the archive record name is invalid")
            envelope = _Envelope.model_validate_json(_read_bytes(path))
            if (
                envelope.document_id != envelope.enriched.document_id
                or (document_id is not None and envelope.document_id != document_id)
                or path.name != _key(envelope.document_id) + ".json"
                or envelope.content_hash != envelope.enriched.content_hash()
            ):
                raise ValueError("record identity or content integrity mismatch")
            envelope.payload()
            return envelope
        except FileNotFoundError as failure:
            if document_id is not None:
                raise ArchiveDocumentNotFound(document_id) from failure
            raise ArchiveRejected("a listed archive record is missing") from failure
        except OSError as failure:
            raise ArchiveUnavailable(
                "the archive record could not be read", subject=document_id
            ) from failure
        except (ValueError, ValidationError, binascii.Error) as failure:
            raise ArchiveRejected(
                "the archive record is invalid or unsupported", subject=document_id
            ) from failure

    def load(self, document_id: str) -> EnrichedConversation:
        return self._read(self._path(document_id), document_id).enriched

    def load_original(self, document_id: str) -> OriginalPayload:
        return self._read(self._path(document_id), document_id).payload()

    def _path(self, document_id: str) -> Path:
        try:
            return self._directory / (_key(document_id) + ".json")
        except UnicodeError as failure:
            raise ArchiveRejected("the document identity is invalid") from failure

    def iter_document_ids(self, *, source: Source | None = None) -> Iterator[str]:
        return _Identifiers(self, source)


class _Identifiers(Iterator[str]):
    """Advance before validating, so a corrupt record cannot close the listing."""

    def __init__(self, archive: LocalRawArchive, source: Source | None) -> None:
        self._archive = archive
        self._source = source
        self._entries: os.ScandirIterator | None = None
        self._done = False

    def __next__(self) -> str:
        if self._done:
            raise StopIteration
        try:
            if self._entries is None:
                # A failure to start a listing concerns the root, not one entry. Report it
                # once; a pipeline that catches boundary errors must be able to finish.
                self._done = True
                self._archive._check_directory()
                try:
                    self._entries = os.scandir(self._archive._directory)
                except FileNotFoundError:
                    self.close()
                    raise StopIteration from None
                self._done = False
            while True:
                entry = next(self._entries)
                if entry.name.startswith(".") and entry.name.endswith(".tmp"):
                    continue
                envelope = self._archive._read(Path(entry.path))
                if self._source is None or envelope.enriched.conversation.source == self._source:
                    return envelope.document_id
        except StopIteration:
            self.close()
            raise
        except OSError as failure:
            self.close()
            raise ArchiveUnavailable("the archive could not be enumerated") from failure

    def close(self) -> None:
        self._done = True
        if self._entries is not None:
            self._entries.close()

    def __del__(self) -> None:
        self.close()
