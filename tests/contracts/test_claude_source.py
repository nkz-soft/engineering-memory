"""The real Claude reader against every source rule, with no failure-hook skips."""

import pytest

from engineering_memory.ingestion.claude_chat import ClaudeChatExportSource
from tests.contracts.source import ConversationSourceContract
from tests.synthetic import claude_export as synth


class TestClaudeSource(ConversationSourceContract):
    @pytest.fixture(autouse=True)
    def workspace(self, tmp_path):
        self.root = tmp_path
        self.counter = 0

    def export(self, values):
        self.counter += 1
        return ClaudeChatExportSource(synth.write(self.root / f"{self.counter}.json", values))

    def make_source(self, conversations):
        return self.export([synth.from_conversation(c) for c in conversations])

    def make_source_with_one_unreadable(self, conversations):
        values = [synth.from_conversation(c) for c in conversations]
        values[1]["created_at"] = "invalid"
        return self.export(values)

    def make_unreachable_source(self):
        return ClaudeChatExportSource(self.root / "absent.json")
