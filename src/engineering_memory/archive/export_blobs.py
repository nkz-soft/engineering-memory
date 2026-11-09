"""Content-addressed originals for acquired ZIPs, separate from conversation envelopes."""

import os
import re
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from hashlib import file_digest, sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Protocol

from engineering_memory.archive.local import _mkdir, _publish, _redirected
from engineering_memory.ingestion.acquisition_source import (
    AcquisitionError,
    ExportCandidate,
    file_stamp,
    local_file,
)

_CHUNK = 1024 * 1024


@dataclass(frozen=True)
class StagedExport:
    path: Path
    digest: str


class ExportBlobs(Protocol):
    def stage(
        self, candidate: ExportCandidate, *, max_bytes: int
    ) -> AbstractContextManager[StagedExport]: ...

    def publish(self, staged: StagedExport) -> Path: ...

    def verified_path(self, digest: str) -> Path: ...

    def find_published(self, digest: str) -> Path | None: ...


class LocalExportBlobs:
    def __init__(self, archive_root: Path) -> None:
        self.root = archive_root
        self.directory = archive_root / "exports" / "chatgpt"

    def _check_directory(self) -> None:
        if any(_redirected(path) for path in (self.root, self.directory.parent, self.directory)):
            raise AcquisitionError("unsafe_archive")

    @contextmanager
    def stage(self, candidate: ExportCandidate, *, max_bytes: int) -> Iterator[StagedExport]:
        temporary = None
        try:
            self._check_directory()
            _mkdir(self.directory)
            digest = sha256()
            total = 0
            if local_file(candidate.path) != candidate.stamp:
                raise AcquisitionError("export_changed")
            if candidate.stamp[2] > max_bytes:
                raise AcquisitionError("export_limit")
            with (
                candidate.path.open("rb") as source,
                NamedTemporaryFile(dir=self.directory, suffix=".staging", delete=False) as output,
            ):
                temporary = Path(output.name)
                opened_stamp = file_stamp(os.fstat(source.fileno()))
                # Windows can report a different change time through an open handle.
                if opened_stamp[:4] != candidate.stamp[:4]:
                    raise AcquisitionError("export_changed")
                while chunk := source.read(_CHUNK):
                    total += len(chunk)
                    if total > max_bytes:
                        raise AcquisitionError("export_limit")
                    digest.update(chunk)
                    output.write(chunk)
                if (
                    total != candidate.stamp[2]
                    or file_stamp(os.fstat(source.fileno())) != opened_stamp
                    or local_file(candidate.path) != candidate.stamp
                ):
                    raise AcquisitionError("export_changed")
                output.flush()
                os.fsync(output.fileno())
        except OSError as error:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise AcquisitionError("archive_unavailable") from error
        except BaseException:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise
        try:
            yield StagedExport(temporary, digest.hexdigest())
        finally:
            temporary.unlink(missing_ok=True)

    def _path(self, digest: str) -> Path:
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise AcquisitionError("archive_integrity")
        self._check_directory()
        return self.directory / f"{digest}.zip"

    def publish(self, staged: StagedExport) -> Path:
        path = self._path(staged.digest)
        try:
            if path.exists() or _redirected(path):
                return self.verified_path(staged.digest)
            _publish(staged.path, path)
        except OSError as error:
            raise AcquisitionError("archive_unavailable") from error
        return path

    def verified_path(self, digest: str) -> Path:
        path = self.find_published(digest)
        if path is None:
            raise AcquisitionError("archive_unavailable")
        return path

    def find_published(self, digest: str) -> Path | None:
        path = self._path(digest)
        try:
            local_file(path)
            with path.open("rb") as source:
                if file_digest(source, "sha256").hexdigest() != digest:
                    raise AcquisitionError("archive_integrity")
        except FileNotFoundError:
            return None
        except OSError as error:
            raise AcquisitionError("archive_unavailable") from error
        return path
