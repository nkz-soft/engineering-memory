"""Nonblocking, process-owned acquisition lock for a local import-state store."""

import errno
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from engineering_memory.ingestion.acquisition_source import AcquisitionError


@contextmanager
def acquisition_lock(state_path: Path) -> Iterator[bool]:
    lock = state_path.with_name(f"{state_path.name}.acquire.lock")
    try:
        lock.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if lock.is_symlink() or lock.is_junction():
            raise AcquisitionError("lock_unavailable")
        descriptor = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as error:
        raise AcquisitionError("lock_unavailable") from error

    with os.fdopen(descriptor, "rb+") as stream:
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EAGAIN):
                raise AcquisitionError("lock_unavailable") from error
            yield False
        else:
            yield True
