"""Private Windows file operations: readers permit rename, writers publish with write-through.

Only imported by the concrete archive on Windows; never by the archive interface.
"""

from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes
from pathlib import Path

_kernel = ctypes.WinDLL("kernel32", use_last_error=True)
_create = _kernel.CreateFileW
_create.argtypes = [
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HANDLE,
]
_create.restype = wintypes.HANDLE
_move = _kernel.MoveFileExW
_move.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
_move.restype = wintypes.BOOL
_close = _kernel.CloseHandle
_close.argtypes = [wintypes.HANDLE]
_close.restype = wintypes.BOOL


def _absolute(path: Path) -> str:
    # Extended-length Windows paths disable dot-segment normalization. Normalize lexically
    # before adding the prefix, without resolving symlinks past the archive's safety checks.
    value = os.path.abspath(path)
    if value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    return "\\\\?\\" + value


def read_bytes(path: Path) -> bytes:
    import msvcrt

    # GENERIC_READ; FILE_SHARE_READ | WRITE | DELETE; OPEN_EXISTING.
    handle = _create(_absolute(path), 0x80000000, 7, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        _close(handle)
        raise
    with os.fdopen(descriptor, "rb") as stream:
        return stream.read()


def publish(temporary: Path, destination: Path) -> None:
    # MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH; same-directory move only.
    for attempt in range(8):
        if _move(_absolute(temporary), _absolute(destination), 0x1 | 0x8):
            return
        error = ctypes.get_last_error()
        # Windows can keep a replaced file delete-pending while another process closes a
        # metadata/read handle. Retry only these contention statuses, with a bounded budget.
        if error not in (5, 32) or attempt == 7:
            raise ctypes.WinError(error)
        time.sleep(0.002 * 2**attempt)
