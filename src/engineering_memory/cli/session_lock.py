"""Nonblocking run ownership scoped to a local import-state file."""

import errno
import os
from contextlib import contextmanager
from pathlib import Path


class CaptureBusy(Exception):
    """Another process holds the capture lock for this state path."""


@contextmanager
def capture_lock(state_path: Path):
    state_path = state_path.resolve()
    lock_path = state_path.with_name(state_path.name + ".sessions.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise CaptureBusy from None
            raise
        # Closing the descriptor releases the lock, including on process exit. Keep the
        # empty file in place so concurrent callers always lock the same filesystem entry.
        yield
