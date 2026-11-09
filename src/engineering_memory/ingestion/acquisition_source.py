"""Local discovery and readiness checks before archive staging."""

import json
import stat
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal, Protocol

Mode = Literal["manual", "watcher"]
FileStamp = tuple[int, int, int, int, int]


class AcquisitionError(Exception):
    """A safe, operator-visible acquisition failure category."""


def file_stamp(info) -> FileStamp:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def local_file(path: Path) -> FileStamp:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_junction():
        raise AcquisitionError("unsafe_export")
    return file_stamp(info)


@dataclass(frozen=True)
class ExportCandidate:
    path: Path
    mode: Mode
    stamp: FileStamp


class ExportSource(Protocol):
    def discover(self) -> Iterable[ExportCandidate]: ...


@dataclass(frozen=True)
class ManualExportSource:
    path: Path

    def discover(self) -> Iterable[ExportCandidate]:
        if self.path.suffix.lower() != ".zip":
            raise AcquisitionError("invalid_export")
        try:
            return (ExportCandidate(self.path, "manual", local_file(self.path)),)
        except OSError as error:
            raise AcquisitionError("export_unavailable") from error


@dataclass(frozen=True)
class InboxExportSource:
    inbox: Path
    observations: Path
    completed: Callable[[str], bool] | None = None

    def discover(self) -> Iterable[ExportCandidate]:
        try:
            if self.inbox.is_symlink() or self.inbox.is_junction():
                raise AcquisitionError("unsafe_inbox")
            previous = self._read_observations()
            current = {}
            ready = []
            next_order = max((entry[1] for entry in previous.values()), default=0) + 1
            # Preserve first-observed order, with name order for simultaneous arrivals.
            paths = sorted(self.inbox.iterdir())
            for path in paths:
                if path.suffix.lower() != ".zip":
                    continue
                try:
                    stamp = local_file(path)
                except FileNotFoundError:
                    continue
                old = previous.get(path.name)
                unchanged = old is not None and old[0] == list(stamp)
                if unchanged:
                    order, digest = old[1:]
                else:
                    order, digest = next_order, None
                    next_order += 1
                current[path.name] = [list(stamp), order, digest]
                complete = (
                    digest is not None and self.completed is not None and self.completed(digest)
                )
                if unchanged and not complete:
                    ready.append((order, ExportCandidate(path, "watcher", stamp)))
            if current != previous:
                self._save_observations(current)
            return tuple(candidate for _, candidate in sorted(ready, key=lambda item: item[0]))
        except OSError as error:
            raise AcquisitionError("inbox_unavailable") from error

    def acknowledge(self, candidate: ExportCandidate, digest: str) -> None:
        """Avoid re-reading an unchanged archive every scheduled check."""
        try:
            observations = self._read_observations()
            old = observations.get(candidate.path.name)
            if old is not None and old[0] == list(candidate.stamp):
                old[2] = digest
                self._save_observations(observations)
        except OSError as error:
            raise AcquisitionError("inbox_unavailable") from error

    def _read_observations(self) -> dict:
        try:
            result = json.loads(self.observations.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (ValueError, UnicodeError):
            return {}
        if not isinstance(result, dict):
            return {}
        return {
            name: entry
            for name, entry in result.items()
            if isinstance(entry, list)
            and len(entry) == 3
            and isinstance(entry[0], list)
            and type(entry[1]) is int
            and (entry[2] is None or isinstance(entry[2], str))
        }

    def _save_observations(self, observations: dict) -> None:
        temporary = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.observations.parent, delete=False
            ) as output:
                temporary = Path(output.name)
                output.write(json.dumps(observations))
            temporary.replace(self.observations)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
