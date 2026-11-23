"""Exercise an installed client registration through the regular Ubuntu launcher."""

import argparse
import os
import select
import shlex
import subprocess
import time
from pathlib import Path
from tempfile import TemporaryDirectory

_RESPONSES = (
    (b"Open the existing settings and MCP configuration? [y/N]", b"y\n"),
    (b"Review provider and workstation settings? [y/N]:", b"n\n"),
    (b"Set up engineering-memory for Codex CLI? [y/N]:", b"y\n"),
)
_SUCCESS = b"Codex CLI: saved. Local MCP check: passed."


def _exercise(launcher: Path, package: Path, environment: dict[str, str]) -> tuple[int, bytes]:
    command = shlex.join(["bash", str(launcher), str(package)])
    transcript = bytearray()
    deadline = time.monotonic() + 180
    with subprocess.Popen(
        ["script", "--quiet", "--return", "--command", command, os.devnull],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=environment,
    ) as process:
        assert process.stdin is not None and process.stdout is not None
        next_prompt = iter(_RESPONSES)
        response = next(next_prompt, None)
        try:
            while True:
                remaining = max(0, deadline - time.monotonic())
                readable, _, _ = select.select([process.stdout], [], [], remaining)
                if not readable:
                    raise TimeoutError("Ubuntu launcher did not finish")
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    return process.wait(timeout=5), bytes(transcript)
                transcript.extend(chunk)
                if response and response[0] in transcript:
                    process.stdin.write(response[1])
                    process.stdin.flush()
                    response = next(next_prompt, None)
        finally:
            if process.poll() is None:
                process.kill()


def verify(launcher: Path, package: Path, scratch: Path) -> None:
    home, binaries = scratch / "home", scratch / "bin"
    home.mkdir()
    binaries.mkdir()
    for name, status in (("docker", 1), ("codex", 91)):
        executable = binaries / name
        executable.write_text(f"#!/bin/sh\nexit {status}\n", encoding="utf-8")
        executable.chmod(0o700)

    codex_profile = scratch / "codex"
    environment = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{binaries}:{os.environ['PATH']}",
        "CODEX_HOME": str(codex_profile),
        "CLAUDE_CONFIG_DIR": str(scratch / "claude"),
        "XDG_CONFIG_HOME": str(scratch / "config"),
        "XDG_DATA_HOME": str(scratch / "data"),
    }
    app = Path("/opt/engineering-memory/engineering-memory")
    before = app.stat()
    status, transcript = _exercise(launcher, package, environment)
    after = app.stat()
    if (before.st_ino, before.st_mtime_ns) != (after.st_ino, after.st_mtime_ns):
        raise RuntimeError("Ubuntu configuration-only setup replaced the existing executable")
    if status != 0 or _SUCCESS not in transcript or not (codex_profile / "config.toml").is_file():
        lines = transcript.decode(errors="replace").splitlines()
        raise RuntimeError(
            "Ubuntu launcher did not save and verify the registration.\n" + "\n".join(lines[-20:])
        )
    print("Ubuntu launcher: Codex CLI registration saved and local MCP verified")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("launcher", type=Path)
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="engineering-memory-launcher-") as temporary:
        verify(args.launcher.absolute(), args.package.absolute(), Path(temporary))


if __name__ == "__main__":
    main()
