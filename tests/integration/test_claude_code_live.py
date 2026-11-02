"""Real-engine root-cause recall from a tool result, scoped to its actual project."""

import json
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
from tests.synthetic import claude_code as synth


@pytest.mark.skipif(
    os.environ.get("ENGINEERING_MEMORY_LIVE_CONTRACT") != "1",
    reason="requires isolated live contract stack",
)
def test_live_tool_root_cause_recall(configured, monkeypatch):  # noqa: F811
    root, _ = configured
    url = os.environ.get("ENGINEERING_MEMORY_LIVE_STORE_URL", "http://127.0.0.1:8889")
    bank = "synthetic-code-" + uuid4().hex
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", url)
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BANK_ID", bank)
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", HindsightStore)
    settings = load_settings()
    try:
        provision(settings.hindsight)
        records = synth.debugging()
        records[2]["message"]["content"][1]["content"] = (
            "Synthetic contract fact: Orchard relay fails because port zero is disabled."
        )
        records[1]["message"]["content"][1]["input"]["command"] += (
            " password=" + "synthetic-secret-123"
        )
        path = synth.write(root / "session.jsonl", records)
        args = ["--source", "claude-code", "--export", str(path)]
        assert invoke(args)["imported"] == 1
        assert invoke(args)["skipped"] == 1
        with HindsightStore(settings.hindsight) as store:
            access = MemoryAccess(store, LocalRawArchive(root / "archive"))
            found = access.search_memory(
                query="Why does the Orchard relay fail?",
                tags=["source:claude-code", "project:orchard"],
            )["results"]
            assert found and all(row["document_id"] == "claude-code:session-one" for row in found)
            assert "port zero" in json.dumps(found).lower()
            opened = json.dumps(access.get_conversation(document_id="claude-code:session-one"))
            assert "port zero" in opened and "new_string" in opened
            assert "synthetic-secret-123" not in opened
            assert not access.search_memory(query="relay", tags=["project:other"])["results"]
    finally:
        with httpx.Client(base_url=url, trust_env=False) as client:
            assert client.delete(f"/v1/default/banks/{bank}").status_code in {200, 204, 404}
