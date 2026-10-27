"""Bind the real file-backed adapter to every shared import-state rule."""

import sqlite3
from uuid import uuid4

import pytest

from engineering_memory.ingestion.sqlite_state import SQLiteImportState
from tests.contracts.state import ImportStateContract


class TestSQLiteImportState(ImportStateContract):
    @pytest.fixture(autouse=True)
    def storage(self, tmp_path):
        self.root = tmp_path
        self.locks = []
        yield
        for lock in self.locks:
            lock.close()

    def make_state(self):
        state = SQLiteImportState(self.root / f"{uuid4()}.db")
        state.initialize()
        return state

    def reopen(self, state):
        state.close()
        other = SQLiteImportState(state.path)
        other.validate()
        return other

    def make_unavailable_state(self):
        state = self.make_state()
        lock = sqlite3.connect(state.path)
        lock.execute("BEGIN EXCLUSIVE")
        self.locks.append(lock)
        return state

    def make_corrupt_state(self):
        state = self.make_state()
        state.path.write_bytes(b"invalid database")
        return state
