"""Locate the native installer payload and its per-user profile."""

import sys
from pathlib import Path

from engineering_memory.settings import workstation_locations


def locations() -> tuple[Path, Path]:
    return workstation_locations()


def is_installed() -> bool:
    return bool(getattr(sys, "frozen", False))


def deployment_file() -> Path:
    root = Path(sys._MEIPASS) if is_installed() else Path(__file__).resolve().parents[2]
    return root / "deploy" / "workstation" / "compose.yaml"
