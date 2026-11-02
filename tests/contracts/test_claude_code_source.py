"""Every ConversationSource rule against real session files."""

import pytest

from engineering_memory.ingestion.claude_code import ClaudeCodeSessionSource
from tests.contracts.source import ConversationSourceContract
from tests.synthetic import claude_code as synth


class TestClaudeCodeSource(ConversationSourceContract):
    @pytest.fixture(autouse=True)
    def workspace(self, tmp_path):
        self.root = tmp_path
        self.counter = 0

    def export(self, conversations, bad=False):
        self.counter += 1
        directory = self.root / str(self.counter)
        directory.mkdir()
        for index, c in enumerate(conversations):
            records = [
                dict(
                    synth.record(m.role.value, m.text),
                    sessionId=c.source_id,
                    uuid=f"turn-{i}",
                    timestamp=m.sent_at.isoformat(),
                )
                for i, m in enumerate(c.messages)
            ]
            if bad and index == 1:
                records[0]["timestamp"] = "invalid"
            synth.write(directory / f"{index}.jsonl", records)
        return ClaudeCodeSessionSource(directory)

    def make_source(self, conversations):
        return self.export(conversations)

    def make_source_with_one_unreadable(self, conversations):
        return self.export(conversations, bad=True)

    def make_unreachable_source(self):
        return ClaudeCodeSessionSource(self.root / "absent")
