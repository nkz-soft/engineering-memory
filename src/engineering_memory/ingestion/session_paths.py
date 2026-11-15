"""Open capture directories without traversing symbolic links or reparse points."""

import os
import stat
from contextlib import ExitStack, contextmanager
from pathlib import Path

if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    _open_windows = _kernel.CreateFileW
    _open_windows.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    _open_windows.restype = wintypes.HANDLE
    _close_windows = _kernel.CloseHandle
    _close_windows.argtypes = (wintypes.HANDLE,)
    _close_windows.restype = wintypes.BOOL
    _handle_info = _kernel.GetFileInformationByHandleEx
    _handle_info.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD)
    _handle_info.restype = wintypes.BOOL
    _handle_path = _kernel.GetFinalPathNameByHandleW
    _handle_path.argtypes = (wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD)
    _handle_path.restype = wintypes.DWORD
    _invalid_handle = wintypes.HANDLE(-1).value


class RedirectedPath(Exception):
    """Capture will not traverse this path."""


def _check_redirect(info: os.stat_result) -> None:
    if stat.S_ISLNK(info.st_mode) or (
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    ):
        raise RedirectedPath


def _windows_attributes(handle: int) -> int:
    attribute_tag_info = 9
    info = (wintypes.DWORD * 2)()
    if not _handle_info(handle, attribute_tag_info, ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    attributes = info[0]
    if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise RedirectedPath
    return attributes


def _verified_windows_handle(
    path: Path, parent: Path | None, *, directory: bool
) -> tuple[int, Path]:
    # Open the entry itself and deny delete sharing to pin its name while in use.
    share_read_and_write = 3
    open_existing = 3
    open_reparse_point = 0x00200000
    backup_semantics = 0x02000000
    access = 0x20 if directory else 0x80000000  # FILE_TRAVERSE or GENERIC_READ
    handle = _open_windows(
        str(path),
        access,
        share_read_and_write,
        None,
        open_existing,
        open_reparse_point | backup_semantics,
        None,
    )
    if handle == _invalid_handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        is_directory = bool(_windows_attributes(handle) & stat.FILE_ATTRIBUTE_DIRECTORY)
        if directory and not is_directory:
            raise NotADirectoryError
        if is_directory and not directory:
            raise IsADirectoryError
        name = ctypes.create_unicode_buffer(32768)
        length = _handle_path(handle, name, len(name), 0)
        if not length or length >= len(name):
            raise OSError("cannot obtain a normalized path for the capture handle")
        actual = Path(name.value)
        if parent is not None and actual.parent != parent:
            raise RedirectedPath
    except BaseException:
        _close_windows(handle)
        raise
    return handle, actual


class CaptureDirectory:
    def __init__(self, path: Path, handle: int, *, canonical_path: Path | None = None):
        self.path = path
        self._handle = handle
        self._canonical_path = canonical_path

    def names(self) -> list[str]:
        if self._canonical_path is None:
            return os.listdir(self._handle)
        _windows_attributes(self._handle)
        names = os.listdir(self.path)
        _windows_attributes(self._handle)
        return names

    def stat(self, name: str) -> os.stat_result:
        if self._canonical_path is None:
            info = os.stat(name, dir_fd=self._handle, follow_symlinks=False)
        else:
            info = (self.path / name).lstat()
        _check_redirect(info)
        return info

    @contextmanager
    def open(self, name: str):
        if self._canonical_path is None:

            def open_relative(path: str, flags: int) -> int:
                return os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self._handle)

            with open(name, "rb", opener=open_relative) as stream:
                yield stream
        else:
            handle, _ = _verified_windows_handle(
                self.path / name, self._canonical_path, directory=False
            )
            try:
                fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            except BaseException:
                _close_windows(handle)
                raise
            with os.fdopen(fd, "rb") as stream:
                yield stream


@contextmanager
def capture_directory(path: Path):
    with ExitStack() as stack:
        if os.name == "nt":
            canonical = None
            for part in (*reversed(path.parents), path):
                handle, canonical = _verified_windows_handle(part, canonical, directory=True)
                stack.callback(_close_windows, handle)
            yield CaptureDirectory(path, handle, canonical_path=canonical)
        else:
            fd = None
            for index, part in enumerate(path.parts, 1):
                access = (
                    os.O_RDONLY if index == len(path.parts) else getattr(os, "O_PATH", os.O_RDONLY)
                )
                fd = os.open(part, access | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                stack.callback(os.close, fd)
            yield CaptureDirectory(path, fd)
