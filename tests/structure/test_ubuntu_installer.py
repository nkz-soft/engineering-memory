import hashlib
import os
import select
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or os.geteuid() == 0,
    reason="requires a regular Linux user and Bash",
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("failure", "calls", "message"),
    [
        ("", ["apt", "setup"], ""),
        ("checksum", [], "checksum"),
        ("metadata", [], "package"),
        ("newer", [], "newer"),
        ("apt", ["apt"], "installation failed"),
        ("version", ["apt"], "installed version"),
        ("status", ["apt"], "installed version"),
        ("setup", ["apt", "setup"], "Retry"),
        ("terminal", [], "interactive terminal"),
    ],
)
def test_ubuntu_launcher_preserves_install_order(tmp_path, failure, calls, message):
    import pty

    script = ROOT / "packaging/workstation/install-ubuntu.sh"
    launcher = tmp_path / "install.sh"
    launcher.write_text(script.read_text(encoding="utf-8").replace("@VERSION@", "0.0.1"))
    downloads = tmp_path / "my downloads"
    downloads.mkdir()
    package = downloads / "engineering-memory_0.0.1_amd64.deb"
    package.write_bytes(b"synthetic package")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    if failure == "checksum":
        digest = "0" * 64
    downloads.joinpath(f"{package.name}.sha256").write_text(f"{digest}  {package.name}\n")

    # Stub the privileged handoff and capture its arguments without changing host packages.
    hooks = tmp_path / "test-hooks.sh"
    hooks.write_text(
        """
dpkg-deb() {
  test "$1" = --field && test "$2" = "$TEST_PACKAGE" || return 42
  case "$3" in
    Package) echo engineering-memory ;;
    Architecture) echo amd64 ;;
    Version) if [[ "$TEST_FAILURE" == metadata ]]; then echo 0.1.0; else echo 0.0.1; fi ;;
    *) return 42 ;;
  esac
}
dpkg-query() {
  test "$*" = '-W -f=${db:Status-Status} ${Version} engineering-memory' || return 42
  if [[ "$TEST_FAILURE" == newer || "$TEST_FAILURE" == version && -e "$TEST_CALLS" ]]; then
    echo 'installed 0.1.0'
  elif [[ -e "$TEST_CALLS" ]]; then
    if [[ "$TEST_FAILURE" == status ]]; then echo 'unpacked 0.0.1'; else echo 'installed 0.0.1'; fi
  else
    return 1
  fi
}
sudo() {
  test "$#" -eq 6 && test "$1 $2 $3 $4 $5" = 'apt-get install --reinstall -y --' &&
    test "$6" = "$TEST_PACKAGE" || return 42
  echo apt >> "$TEST_CALLS"
  [[ "$TEST_FAILURE" != apt ]]
}
/usr/bin/engineering-memory() {
  test "$#" -eq 1 && test "$1" = setup || return 42
  echo setup >> "$TEST_CALLS"
  [[ "$TEST_FAILURE" != setup ]]
}
""",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "BASH_ENV": str(hooks),
        "TEST_CALLS": str(tmp_path / "calls"),
        "TEST_FAILURE": failure,
        "TEST_PACKAGE": str(package),
    }
    master, terminal = pty.openpty()
    try:
        result = subprocess.run(
            [shutil.which("bash"), str(launcher), str(package)],
            cwd=tmp_path,
            stdin=subprocess.DEVNULL if failure == "terminal" else terminal,
            stdout=terminal,
            stderr=terminal,
            env=env,
            timeout=10,
            check=False,
        )
        readable, _, _ = select.select([master], [], [], 1)
        output = os.read(master, 4096).decode() if readable else ""
    finally:
        os.close(terminal)
        os.close(master)
    log = tmp_path / "calls"
    assert (log.read_text().splitlines() if log.exists() else []) == calls
    assert result.returncode == (1 if failure else 0), output
    assert message in output
