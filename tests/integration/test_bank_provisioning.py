"""Opt-in configuration contract against the pinned engine; no operator bank writes."""

import os
from uuid import uuid4

import httpx
import pytest

from engineering_memory.memory.hindsight.provision import mission_text, provision
from engineering_memory.settings import HindsightSettings

pytestmark = pytest.mark.skipif(
    os.environ.get("ENGINEERING_MEMORY_LIVE_STORE") != "1",
    reason="requires explicit live engine opt-in",
)


def test_fresh_bank_mission_replacement_and_repeat_preserve_config():
    bank = "engineering-memory-provision-contract-" + uuid4().hex
    base = os.environ.get("ENGINEERING_MEMORY_LIVE_STORE_URL", "http://127.0.0.1:8889")
    token = os.environ.get("ENGINEERING_MEMORY_LIVE_STORE_TOKEN")
    settings = HindsightSettings(base_url=base, bank_id=bank, token=token)
    headers = {"Authorization": "Bearer " + token} if token else {}
    root = f"/v1/default/banks/{bank}"
    with httpx.Client(base_url=base, headers=headers, trust_env=False, timeout=30) as client:
        try:
            assert client.get(root + "/config").status_code == 404
            provision(settings)
            assert client.get(root + "/documents").json()["items"] == []
            first = client.get(root + "/config")
            assert first.status_code == 200
            assert first.json()["config"]["retain_mission"] == mission_text()
            provision(settings)
            assert client.get(root + "/config").json() == first.json()
            retained = client.post(
                root + "/memories",
                json={
                    "items": [
                        {
                            "content": "The synthetic Observatory uses port 47291.",
                            "document_id": "synthetic-provision-preservation",
                            "timestamp": "2026-01-01T00:00:00+00:00",
                        }
                    ]
                },
                timeout=240,
            )
            assert retained.status_code == 200
            assert retained.json()["success"] is True
            documents = client.get(root + "/documents").json()
            assert documents["items"], "synthetic document was not persisted"
            assert sum(item["memory_unit_count"] for item in documents["items"]) > 0
            changed = client.patch(
                root + "/config",
                json={
                    "updates": {
                        "retain_mission": "Synthetic older mission.",
                        "reflect_mission": "Synthetic reflection policy to preserve.",
                    }
                },
            )
            assert changed.status_code == 200
            provision(settings)
            current = client.get(root + "/config").json()["config"]
            assert client.get(root + "/documents").json() == documents
            assert current["retain_mission"] == mission_text()
            assert current["reflect_mission"] == "Synthetic reflection policy to preserve."
        finally:
            assert bank.startswith("engineering-memory-provision-contract-")
            assert client.delete(root).status_code in {200, 204, 404}
