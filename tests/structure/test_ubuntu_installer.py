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
    ("scenario", "reply", "calls", "message", "success"),
    [
        ("fresh", "", ["apt", "setup"], "", True),
        ("orphan", "y", ["apt", "setup"], "Repair", True),
        ("redirected", "", [], "redirected", False),
        ("checksum", "", [], "checksum", False),
        ("query-error", "", [], "package status", False),
        ("changed-package", "", [], "checksum", False),
        ("metadata", "", [], "package", False),
        ("newer", "", [], "newer", False),
        ("update", "y", ["apt", "setup"], "Update", True),
        ("update", "n", [], "Update", True),
        ("identical", "y", ["setup --configure-only"], "already installed", True),
        ("identical", "n", [], "already installed", True),
        ("different", "y", ["apt --reinstall", "setup"], "different build", True),
        ("different", "n", [], "different build", True),
        ("damaged", "y", ["apt --reinstall", "setup"], "Repair", True),
        ("legacy", "y", ["apt --reinstall", "setup"], "Repair", True),
        ("unpacked", "y", ["apt --reinstall", "setup"], "Repair", True),
        ("apt", "", ["apt"], "installation failed", False),
        ("version", "", ["apt"], "installed package", False),
        ("status", "", ["apt"], "installed package", False),
        ("wrong-build", "", ["apt"], "installed package", False),
        ("setup", "", ["apt", "setup"], "Retry", False),
        ("terminal", "", [], "interactive terminal", False),
        ("silent-fresh", "", ["apt -n"], "", True),
        ("silent-update", "", ["apt -n"], "Update", True),
        ("silent-identical", "", [], "already installed", True),
        ("silent-different", "", [], "interactive", False),
        ("silent-damaged", "", [], "interactive", False),
        ("silent-orphan", "", [], "interactive", False),
        ("silent-newer", "", [], "newer", False),
    ],
)
def test_ubuntu_launcher_preserves_install_order(
    tmp_path, scenario, reply, calls, message, success
):
    import pty

    script = ROOT / "packaging/workstation/install-ubuntu.sh"
    launcher = tmp_path / "install.sh"
    launcher.write_text(script.read_text(encoding="utf-8").replace("@VERSION@", "0.0.1"))
    downloads = tmp_path / "my downloads"
    downloads.mkdir()
    package = downloads / "engineering-memory_0.0.1_amd64.deb"
    package.write_bytes(b"synthetic package")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    if scenario == "checksum":
        digest = "0" * 64
    downloads.joinpath(f"{package.name}.sha256").write_text(f"{digest}  {package.name}\n")

    hooks = tmp_path / "test-hooks.sh"
    hooks.write_text(
        r"""
test() {
  case "${2-}" in
    /opt/engineering-memory)
      if [[ "$1" == -L ]]; then [[ "$TEST_SCENARIO" == redirected ]]
      else [[ "$TEST_SCENARIO" == orphan ]]; fi ;;
    /usr/bin/engineering-memory) return 1 ;;
    *) builtin test "$@" ;;
  esac
}
dpkg-deb() {
  test "$1" = --field && test "$2" = "$TEST_PACKAGE" || return 42
  case "$3" in
    Package) echo engineering-memory ;;
    Architecture) echo amd64 ;;
    Version) if [[ "$TEST_SCENARIO" == metadata ]]; then echo 0.1.0; else echo 0.0.1; fi ;;
    X-Engineering-Memory-Build) echo "$TEST_NEW_BUILD" ;;
    *) return 42 ;;
  esac
}
dpkg-query() {
  if [[ "$1" == -L ]]; then
    printf '%s\n' /. /opt /opt/engineering-memory \
      /opt/engineering-memory/engineering-memory /usr/bin/engineering-memory
    return
  fi
  test "$1" = -W && test "${!#}" = engineering-memory || return 42
  if [[ "$TEST_SCENARIO" == query-error || "$TEST_SCENARIO" == changed-package ]]; then
    if [[ -e "$TEST_CALLS.query" ]]; then
      if [[ "$TEST_SCENARIO" == query-error ]]; then return 2; fi
      printf 'changed package' > "$TEST_PACKAGE"
    fi
    touch "$TEST_CALLS.query"
    return 1
  fi
  if [[ -e "$TEST_CALLS" ]]; then
    case "$TEST_SCENARIO" in
      version) printf 'installed\t0.1.0\t%s\n' "$TEST_NEW_BUILD" ;;
      status) printf 'unpacked\t0.0.1\t%s\n' "$TEST_NEW_BUILD" ;;
      wrong-build) printf 'installed\t0.0.1\t%s\n' "$TEST_OLD_BUILD" ;;
      *) printf 'installed\t0.0.1\t%s\n' "$TEST_NEW_BUILD" ;;
    esac
  else
    case "$TEST_SCENARIO" in
      newer) printf 'installed\t0.1.0\t%s\n' "$TEST_OLD_BUILD" ;;
      update) printf 'installed\t0.0.0\t%s\n' "$TEST_OLD_BUILD" ;;
      different) printf 'installed\t0.0.1\t%s\n' "$TEST_OLD_BUILD" ;;
      identical|damaged) printf 'installed\t0.0.1\t%s\n' "$TEST_NEW_BUILD" ;;
      legacy) printf 'installed\t0.0.1\t\n' ;;
      unpacked) printf 'unpacked\t0.0.1\t%s\n' "$TEST_NEW_BUILD" ;;
      *) return 1 ;;
    esac
  fi
}
tar() {
  local entry
  while IFS= read -r -d '' entry; do
    case "$entry" in
      opt/engineering-memory|opt/engineering-memory/engineering-memory) ;;
      usr/bin/engineering-memory) ;;
      *) return 42 ;;
    esac
  done
  if [[ ! -e "$TEST_CALLS" ]]; then
    case "$TEST_SCENARIO" in
      update|different) printf 'old payload'; return ;;
      damaged) return 1 ;;
    esac
  fi
  printf 'new payload'
}
sudo() {
  local action=apt
  if [[ "$1" == -n ]]; then action="$action -n"; shift; fi
  test "$1" = apt-get && test "$2" = install || return 42
  shift 2
  if [[ "$1" == --reinstall ]]; then action="$action --reinstall"; shift; fi
  test "$#" -eq 4 && test "$1 $2 $3" = '--no-allow-downgrades -y --' &&
    test "$4" = "$TEST_PACKAGE" || return 42
  echo "$action" >> "$TEST_CALLS"
  [[ "$TEST_SCENARIO" != apt ]]
}
/usr/bin/engineering-memory() {
  test "$1" = setup || return 42
  echo "$*" >> "$TEST_CALLS"
  [[ "$TEST_SCENARIO" != setup ]]
}
""",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "BASH_ENV": str(hooks),
        "TEST_CALLS": str(tmp_path / "calls"),
        "TEST_SCENARIO": scenario.removeprefix("silent-"),
        "TEST_PACKAGE": str(package),
        "TEST_NEW_BUILD": hashlib.sha256(b"new payload").hexdigest(),
        "TEST_OLD_BUILD": hashlib.sha256(b"old payload").hexdigest(),
    }
    unattended = scenario.startswith("silent-")
    args = [shutil.which("bash"), str(launcher)]
    if unattended:
        args.append("--non-interactive")
    args.append(str(package))
    master, terminal = pty.openpty()
    try:
        if reply:
            os.write(master, f"{reply}\n".encode())
        result = subprocess.run(
            args,
            cwd=tmp_path,
            stdin=subprocess.DEVNULL if unattended or scenario == "terminal" else terminal,
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
    assert (log.read_text().splitlines() if log.exists() else []) == calls, output
    assert result.returncode == (0 if success else 1), output
    assert message in output


def test_deb_identity_ignores_timestamps_and_tracks_symlink_targets(tmp_path):
    script = ROOT / "packaging/workstation/build-deb.sh"
    payload = tmp_path / "payload"
    payload.mkdir()
    executable = payload / "engineering-memory"
    executable.write_bytes(b"fixture installer payload")
    executable.chmod(0o755)
    alias = payload / "runtime-link"
    alias.symlink_to("engineering-memory")
    output = tmp_path / "packages"
    package = output / "engineering-memory_0.0.1_amd64.deb"

    def build_identity():
        subprocess.run(
            ["bash", str(script), str(payload), str(output), "0.0.1"],
            check=True,
            capture_output=True,
        )
        result = subprocess.check_output(
            ["dpkg-deb", "--field", str(package), "X-Engineering-Memory-Build"], text=True
        )
        return result.strip()

    original = build_identity()
    assert len(original) == 64
    os.utime(executable, (10000, 20000))
    assert build_identity() == original
    alias.unlink()
    alias.symlink_to("different-target")
    assert build_identity() != original
