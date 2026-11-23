"""Generate the immutable identity manifest for the Windows workstation payload."""

import argparse
import re
import stat
from hashlib import file_digest, sha256
from pathlib import Path

MANIFEST = "engineering-memory.build"
RECIPE = ("windows.iss", "windows-maintenance.iss")
RELEASE = re.compile(r"(?:0|[1-9][0-9]{0,4})(?:\.(?:0|[1-9][0-9]{0,4})){2}")
COMPONENT = re.compile(r"[A-Za-z0-9_.()+@ -]+")


def digest(path: Path) -> str:
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest()


def is_redirected(path: Path) -> bool:
    return path.is_symlink() or bool(
        getattr(path.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def build_manifest(root: Path, version: str) -> str:
    if not RELEASE.fullmatch(version) or any(int(part) > 65535 for part in version.split(".")):
        raise ValueError("expected a three-part Windows release version")

    inventory = {}
    if not root.is_dir() or is_redirected(root):
        raise ValueError("invalid or redirected Windows payload directory")
    for directory, dirs, files in root.walk(on_error=raise_walk_error):
        for name in dirs + files:
            path = directory / name
            if is_redirected(path) or not COMPONENT.fullmatch(name) or name.endswith((".", " ")):
                raise ValueError("invalid or redirected Windows payload path")
        for name in files:
            path = directory / name
            relative = path.relative_to(root).as_posix()
            if relative == MANIFEST:
                continue
            if not path.is_file() or relative.lower() in inventory:
                raise ValueError("invalid or duplicate Windows payload entry")
            inventory[relative.lower()] = (relative, digest(path))

    if "engineering-memory.exe" not in inventory or not any(
        path.startswith("_internal/") for path in inventory
    ):
        raise ValueError("Windows payload is missing the launcher or bundled runtime")

    recipe = Path(__file__).parent
    scripts = [
        sha256((recipe / name).read_text(encoding="utf-8").encode()).hexdigest() for name in RECIPE
    ]
    fingerprint = sha256("\n".join(scripts).encode()).hexdigest()
    lines = ["EM-BUILD-1", version, fingerprint]
    for path, checksum in sorted(inventory.values(), key=lambda entry: entry[0].lower()):
        lines.append(f"{checksum} {path}")
    payload = ("\n".join(lines) + "\n").encode("ascii")
    (root / MANIFEST).write_bytes(payload)
    return sha256(payload).hexdigest()


def raise_walk_error(error: OSError) -> None:
    raise error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("payload", type=Path)
    args = parser.parse_args()
    try:
        identity = build_manifest(args.payload, args.version)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(identity)


if __name__ == "__main__":
    main()
