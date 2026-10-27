"""Durable filesystem implementation against the shared archive contract."""

from pathlib import Path

import pytest

from engineering_memory.archive import RawArchive
from tests.contracts.archive import RawArchiveContract


def local(root: Path):
    from engineering_memory.archive import local as implementation

    assert hasattr(implementation, "LocalRawArchive"), "local archive implementation is missing"
    return implementation.LocalRawArchive(root)


class TestLocalRawArchive(RawArchiveContract):
    @pytest.fixture(autouse=True)
    def workspace(self, tmp_path):
        self.root = tmp_path / "archive"

    def make_archive(self) -> RawArchive:
        return local(self.root)

    def reopen(self, archive):
        return local(self.root)

    def make_unavailable_archive(self):
        blocked = self.root.parent / "blocked"
        blocked.write_text("not a directory")
        return local(blocked)

    def make_rejecting_archive(self):
        return None
