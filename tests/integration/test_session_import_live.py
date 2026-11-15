"""Verify automatic capture and source-filtered recall on the isolated contract engine."""

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
from tests.integration.test_claude_cli import configured  # noqa: F401
from tests.integration.test_session_import import PREFIX, capture, settle
from tests.synthetic import claude_code, codex


@pytest.mark.skipif(
    os.environ.get("ENGINEERING_MEMORY_LIVE_CONTRACT") != "1",
    reason="requires isolated live contract stack",
)
def test_capture_recall_both_sources(configured, monkeypatch):  # noqa: F811
    root, _ = configured
    url = os.environ.get("ENGINEERING_MEMORY_LIVE_STORE_URL", "http://127.0.0.1:8889")
    bank = "synthetic-session-import-" + uuid4().hex
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", url)
    monkeypatch.setenv("ENGINEERING_MEMORY_HINDSIGHT__BANK_ID", bank)
    monkeypatch.setattr("engineering_memory.cli.runtime.make_memory", HindsightStore)

    codex_root, claude_root = root / "sessions", root / "projects"
    monkeypatch.setenv(PREFIX + "CODEX_ROOT", str(codex_root))
    monkeypatch.setenv(PREFIX + "CLAUDE_CODE_ROOT", str(claude_root))
    fact = "Synthetic contract fact: Orchard relay fails because port zero is disabled."
    codex_records = codex.debugging()
    codex_records[4]["payload"]["output"] = fact
    codex_records[3]["payload"]["arguments"] += " password=" + "synthetic-secret-123"
    claude_records = claude_code.debugging()
    claude_records[2]["message"]["content"][1]["content"] = fact
    claude_records[1]["message"]["content"][1]["input"]["command"] += (
        " password=" + "synthetic-secret-123"
    )
    settle(codex.write(codex_root / "2026/03/04/rollout-one.jsonl", codex_records))
    settle(claude_code.write(claude_root / "orchard/session.jsonl", claude_records))

    settings = load_settings()
    try:
        provision(settings.hindsight)
        assert [row["imported"] for row in capture()["sources"]] == [1, 1]
        assert [row["unchanged"] for row in capture()["sources"]] == [1, 1]
        with HindsightStore(settings.hindsight) as store:
            access = MemoryAccess(store, LocalRawArchive(root / "archive"))
            for kind in ("codex", "claude-code"):
                document_id = f"{kind}:session-one"
                found = access.search_memory(
                    query="Why does the Orchard relay fail?",
                    tags=[f"source:{kind}", "project:orchard"],
                )["results"]
                assert found and {row["document_id"] for row in found} == {document_id}
                assert "port zero" in json.dumps(found).lower()
                opened = json.dumps(access.get_conversation(document_id=document_id))
                assert "port zero" in opened
                assert "synthetic-secret-123" not in opened
    finally:
        with httpx.Client(base_url=url, trust_env=False) as client:
            assert client.delete(f"/v1/default/banks/{bank}").status_code in {200, 204, 404}
