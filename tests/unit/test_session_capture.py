"""File stability and OS lock behavior for scheduled capture."""

import json
import os
import signal
import subprocess
import sys
import time

import pytest

from tests.synthetic import codex


def test_changed_during_read_is_deferred(tmp_path, monkeypatch):
    try:
        from engineering_memory.ingestion.session_capture import CapturedSessionSource
    except ImportError:
        pytest.fail("the stable capture source is missing", pytrace=False)

    path = codex.write(tmp_path / "one.jsonl", codex.debugging())
    old = time.time() - 600
    os.utime(path, (old, old))
    fstat = os.fstat
    calls = 0

    def append_before_second_fstat(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            with path.open("ab") as stream:
                stream.write(codex.encode([codex.message("assistant", "Resumed")]))
        return fstat(fd)

    monkeypatch.setattr(os, "fstat", append_before_second_fstat)
    source = CapturedSessionSource("codex", tmp_path, 300)
    assert list(source.read()) == []
    assert source.deferred == 1


def test_capture_excludes_redirected_paths(tmp_path):
    try:
        from engineering_memory.ingestion.session_capture import CapturedSessionSource
    except ImportError:
        pytest.fail("the bounded capture source is missing", pytrace=False)

    root = tmp_path / "sessions"
    path = codex.write(tmp_path / "unapproved.jsonl", codex.debugging("excluded"))
    good = codex.write(root / "good.jsonl", codex.debugging("approved"))
    try:
        (root / "redirect.jsonl").symlink_to(path)
    except OSError:
        if sys.platform != "win32":
            raise
        pytest.skip("symlinks require Developer Mode or elevation on Windows")
    old = time.time() - 600
    for candidate in (path, good):
        os.utime(candidate, (old, old))
    source = CapturedSessionSource("codex", root, 300)
    assert [item.conversation.source_id for item in source.read()] == ["approved"]


def test_cli_lock_contention_and_release_on_process_exit(tmp_path, monkeypatch):
    try:
        from engineering_memory.cli.session_lock import capture_lock
    except ImportError:
        pytest.fail("the cross-process capture lock is missing", pytrace=False)

    sessions = tmp_path / "sessions"
    sessions.mkdir()
    state = tmp_path / "state.db"
    monkeypatch.setenv("ENGINEERING_MEMORY_SESSION_IMPORT__CODEX_ROOT", str(sessions))
    monkeypatch.setenv("ENGINEERING_MEMORY_IMPORT_STATE_PATH", str(state))
    rules = tmp_path / "projects.toml"
    rules.touch()
    monkeypatch.setenv("ENGINEERING_MEMORY_PROJECT_RULES_PATH", str(rules))
    monkeypatch.setenv("ENGINEERING_MEMORY_ARCHIVE_ROOT", str(tmp_path / "archive"))
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "http://engine")
    monkeypatch.setenv("ENGINEERING_MEMORY_LLM__BASE_URL", "http://proxy")
    lock_process = (
        "from pathlib import Path; import os, sys; "
        "from engineering_memory.cli.session_lock import capture_lock\n"
        "with capture_lock(Path(sys.argv[1])):\n"
        "    print(os.getpid(), flush=True)\n"
        "    sys.stdin.read()\n"
    )
    with subprocess.Popen(
        [sys.executable, "-c", lock_process, str(state)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    ) as process:
        holder_pid = int(process.stdout.readline())
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from engineering_memory.cli import main; main()",
                    "import-sessions",
                    "--json",
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            assert result.returncode == 1, result.stderr
            assert json.loads(result.stdout)["error"] == "busy"
            assert not state.exists()
        finally:
            # A Windows venv launcher can be the parent of the actual Python worker.
            os.kill(holder_pid, signal.SIGTERM)
            process.wait(timeout=10)
    with capture_lock(state):
        assert not state.exists()


@pytest.mark.skipif(os.name != "posix", reason="uses POSIX directory descriptors and symlinks")
def test_replaced_parent_cannot_redirect_open(tmp_path, monkeypatch):
    from engineering_memory.ingestion.session_capture import CapturedSessionSource

    root = tmp_path / "sessions"
    approved = codex.write(root / "session.jsonl", codex.debugging("approved"))
    outside = codex.write(tmp_path / "outside/session.jsonl", codex.debugging("outside"))
    old = time.time() - 600
    for path in (approved, outside):
        os.utime(path, (old, old))
    approved_inode = approved.stat().st_ino
    opened = []
    open_file = os.open

    def swap_before_open(path, flags, mode=0o777, *, dir_fd=None):
        if os.fspath(path).endswith("session.jsonl"):
            root.rename(tmp_path / "moved")
            root.symlink_to(outside.parent, target_is_directory=True)
            fd = open_file(path, flags, mode, dir_fd=dir_fd)
            opened.append(os.fstat(fd).st_ino)
            return fd
        return open_file(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", swap_before_open)
    source = CapturedSessionSource("codex", root, 300)
    assert not list(source.read())
    assert opened == [approved_inode]
    assert source.deferred == 1


@pytest.mark.skipif(os.name != "nt", reason="checks Windows sharing flags")
def test_open_capture_directory_blocks_rename_on_windows(tmp_path):
    from engineering_memory.ingestion.session_paths import capture_directory

    root = tmp_path / "sessions"
    root.mkdir()
    target = tmp_path / "moved"
    with capture_directory(root), pytest.raises(PermissionError):
        root.rename(target)
    root.rename(target)
    assert target.is_dir()


@pytest.mark.skipif(sys.platform != "linux", reason="uses Linux O_PATH")
def test_capture_root_under_search_only_ancestor(tmp_path):
    from engineering_memory.ingestion.session_paths import capture_directory

    if os.geteuid() == 0:
        pytest.skip("root can read the ancestor despite its mode bits")
    ancestor = tmp_path / "ancestor"
    sessions = ancestor / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "one.jsonl").touch()
    ancestor.chmod(0o100)
    try:
        with capture_directory(sessions) as directory:
            assert directory.names() == ["one.jsonl"]
    finally:
        ancestor.chmod(0o700)
