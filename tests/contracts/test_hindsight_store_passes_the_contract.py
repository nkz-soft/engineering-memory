"""Bind the shared boundary contract to a stateful wire fixture and real engine."""

import json
import os
from uuid import uuid4

import httpx
import pytest

from engineering_memory.memory.hindsight.store import HindsightStore
from engineering_memory.settings import HindsightSettings
from tests.contracts.store import MemoryStoreContract


class TestHindsightStore(MemoryStoreContract):
    def make_store(self):
        documents = {}

        def handler(request):
            if request.method == "GET":
                return httpx.Response(200, json={"status": "completed"})
            body = json.loads(request.content)
            if request.url.path.endswith("/recall"):
                facts = []
                for item in documents.values():
                    if not set(body["tags"]) <= set(item["tags"]):
                        continue
                    messages = json.loads(item["content"])["messages"]
                    facts.append(
                        {
                            "text": " ".join(message["text"] for message in messages),
                            "document_id": item["document_id"],
                            "metadata": item["metadata"],
                            "tags": item["tags"],
                        }
                    )
                return httpx.Response(200, json={"results": facts})
            for item in body["items"]:
                documents[item["document_id"]] = item
            return httpx.Response(
                200, json={"success": True, "async": True, "operation_id": body["operation_id"]}
            )

        return self._with_transport(handler)

    @staticmethod
    def _with_transport(handler):
        return HindsightStore(
            HindsightSettings(base_url="http://engine.invalid"),
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            poll_interval=0,
        )

    def make_rejecting_store(self):
        return self._with_transport(lambda request: httpx.Response(401))

    def make_unavailable_store(self):
        return self._with_transport(lambda request: httpx.Response(503))


@pytest.mark.skipif(
    os.environ.get("ENGINEERING_MEMORY_LIVE_STORE") != "1", reason="live opt-in required"
)
class TestLiveHindsightStore(TestHindsightStore):
    @pytest.fixture(autouse=True)
    def scratch(self):
        self._live_stores = []
        yield
        for store, client, root in self._live_stores:
            store.close()
            response = client.delete(root, timeout=15)
            client.close()
            assert response.status_code in {200, 204, 404}, "scratch-bank cleanup failed"

    def make_store(self):
        bank = "engineering-memory-contract-" + uuid4().hex
        base = os.environ.get("ENGINEERING_MEMORY_LIVE_STORE_URL", "http://127.0.0.1:8889")
        client = httpx.Client(base_url=base, trust_env=False, timeout=30)
        # Provision only this test bank. The product's bank mission remains #17.
        response = client.put(f"/v1/default/banks/{bank}", json={"name": bank})
        assert response.is_success, f"scratch provisioning HTTP {response.status_code}"
        store = HindsightStore(HindsightSettings(base_url=base, bank_id=bank))
        self._live_stores.append((store, client, f"/v1/default/banks/{bank}"))
        return store
