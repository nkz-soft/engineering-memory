"""Build and verify a native CLI payload using the locked release environment."""

import argparse
import platform
import subprocess
import sys
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
NAME = "engineering-memory"
ASSETS = (
    "deploy/workstation/compose.yaml",
    "deploy/workstation/app.env.example",
    "deploy/workstation/compose.env.example",
    "deploy/hindsight/service.yaml",
    "deploy/product/litellm.yaml",
    "docs/operations/workstation-install.md",
    "LICENSE",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    if args.tag != f"v{version}":
        parser.error(f"tag must match the project version v{version}")
    if platform.machine().lower() not in {"x86_64", "amd64"}:
        parser.error("build on an x86_64 host")
    output = args.output.resolve()
    with TemporaryDirectory(prefix="engineering-memory-build-") as temporary:
        scratch = Path(temporary)
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--onedir",
            "--name",
            NAME,
            "--distpath",
            str(output),
            "--workpath",
            str(scratch / "work"),
            "--specpath",
            str(scratch),
            "--copy-metadata",
            NAME,
            "--recursive-copy-metadata",
            "opentelemetry-sdk",
            "--collect-data",
            "engineering_memory",
            "--hidden-import",
            "sqlalchemy.dialects.sqlite.pysqlite",
        ]
        for asset in ASSETS:
            command += ["--add-data", f"{ROOT / asset}:{Path(asset).parent.as_posix()}"]
        subprocess.run([*command, str(Path(__file__).with_name("entry.py"))], check=True, cwd=ROOT)
        executable = output / NAME / (f"{NAME}.exe" if sys.platform == "win32" else NAME)
        result = subprocess.check_output([str(executable), "--version"], text=True, cwd=scratch)
        if result.strip() != f"{NAME} {version}":
            raise SystemExit(f"Unexpected packaged version: {result!r}")


if __name__ == "__main__":
    main()
