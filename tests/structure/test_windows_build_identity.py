import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "engineering-memory.build"


def make_payload(directory):
    runtime = directory / "_internal"
    runtime.mkdir(parents=True)
    (directory / "engineering-memory.exe").write_bytes(b"launcher")
    (runtime / "runtime.dll").write_bytes(b"runtime")


def manifest_command(directory, version="0.0.1"):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "packaging/workstation/windows_manifest.py"),
            version,
            str(directory),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_manifest_identifies_version_and_all_payload_bytes(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    make_payload(first)
    make_payload(second)
    results = [manifest_command(path) for path in (first, second, first)]
    assert [result.returncode for result in results] == [0, 0, 0]
    identity = sha256((first / MANIFEST).read_bytes()).hexdigest()
    assert all(result.stdout.strip() == identity for result in results)
    (second / "_internal/runtime.dll").write_bytes(b"changed")
    assert manifest_command(second).stdout.strip() != identity
    assert manifest_command(first, "0.0.2").stdout.strip() != identity


@pytest.mark.parametrize("version", ["1.2.3rc1", "1.02.3", "1.65536.0", "1.2"])
def test_unsupported_windows_versions_are_rejected(tmp_path, version):
    make_payload(tmp_path)
    result = manifest_command(tmp_path, version)
    assert result.returncode == 2
    assert "expected a three-part Windows release version" in result.stderr
    assert not (tmp_path / MANIFEST).exists()


def test_manifest_requires_the_installed_launcher(tmp_path):
    make_payload(tmp_path)
    (tmp_path / "engineering-memory.exe").unlink()
    result = manifest_command(tmp_path)
    assert result.returncode == 2
    assert "missing the launcher or bundled runtime" in result.stderr
