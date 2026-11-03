"""Every conversation source contract against synthetic Codex snapshots."""

import pytest

from engineering_memory.ingestion.codex import CodexSessionSource
from tests.contracts.source import ConversationSourceContract
from tests.synthetic import codex as synth


class TestCodexSource(ConversationSourceContract):
    @pytest.fixture(autouse=True)
    def workspace(self, tmp_path):
        self.root, self.counter = tmp_path, 0

    def export(self, conversations, bad=False):
        self.counter += 1
        directory = self.root / str(self.counter)
        directory.mkdir()
        for index, c in enumerate(conversations):
            records = [
                synth.record("session_meta", id=c.source_id, timestamp=c.started_at.isoformat())
            ]
            for m in c.messages:
                row = synth.message(m.role.value, m.text)
                row["timestamp"] = m.sent_at.isoformat()
                records.append(row)
            if bad and index == 1:
                records[0]["payload"]["timestamp"] = "invalid"
            synth.write(directory / f"{index}.jsonl", records)
        return CodexSessionSource(directory)

    def make_source(self, conversations):
        return self.export(conversations)

    def make_source_with_one_unreadable(self, conversations):
        return self.export(conversations, bad=True)

    def make_unreachable_source(self):
        return CodexSessionSource(self.root / "absent")
