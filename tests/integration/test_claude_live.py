"""Opt-in real-engine Claude/ChatGPT import and source-filtered recall."""

import os
from uuid import uuid4

import httpx
import pytest

from engineering_memory.access.service import MemoryAccess
from engineering_memory.archive.local import LocalRawArchive
from engineering_memory.memory.hindsight.provision import provision
from engineering_memory.memory.hindsight.store import HindsightStore
from engineering_memory.settings import load_settings
from tests.integration.test_claude_cli import configured, invoke  # noqa: F401
from tests.synthetic import chatgpt_export, claude_export


@pytest.mark.skipif(
    os.environ.get("ENGINEERING_MEMORY_LIVE_CONTRACT") != "1",
    reason="requires isolated live contract stack",
)
def test_live_claude_mixed_recall(configured, monkeypatch):  # noqa: F811
    root, _ = configured
    url = os.environ.get("ENGINEERING_MEMORY_LIVE_STORE_URL", "http://127.0.0.1:8889")
    bank = "synthetic-claude-" + uuid4().hex
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", url)
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BANK_ID", bank)
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", HindsightStore)
    settings = load_settings()
    try:
        provision(settings.hindsight)
        path = claude_export.write(
            root / "conversations.json",
            [
                claude_export.record(
                    "shared", "Synthetic contract fact: Orchard uses a cobalt relay."
                )
            ],
        )
        assert invoke(["--source", "claude-chat", "--export", str(path)])["imported"] == 1
        assert invoke(["--source", "claude-chat", "--export", str(path)])["skipped"] == 1
        chat = chatgpt_export.write_directory(
            root / "chatgpt",
            [
                chatgpt_export.linear_record(
                    "shared",
                    chatgpt_export.message(
                        "user", "Synthetic contract fact: Orchard uses an amber relay."
                    ),
                )
            ],
        )
        assert invoke(["--export", str(chat)])["imported"] == 1
        with HindsightStore(settings.hindsight) as store:
            access = MemoryAccess(store, LocalRawArchive(root / "archive"))
            mixed = access.search_memory(query="Orchard relay")["results"]
            assert {row["document_id"] for row in mixed} == {"chatgpt:shared", "claude-chat:shared"}
            found = access.search_memory(query="cobalt relay", tags=["source:claude-chat"])[
                "results"
            ]
            assert found and all(row["document_id"] == "claude-chat:shared" for row in found)
            assert "cobalt relay" in str(access.get_conversation(document_id="claude-chat:shared"))
    finally:
        with httpx.Client(base_url=url, trust_env=False) as client:
            assert client.delete(f"/v1/default/banks/{bank}").status_code in {200, 204, 404}
