"""Opt-in synthetic compatibility experiments, before adapter implementation.

These inspect the engine contract directly; they are not product E2E evidence.
"""

import os
import time
from uuid import uuid4

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("ENGINEERING_MEMORY_LIVE_STORE") != "1",
    reason="requires explicit live engine opt-in",
)


@pytest.mark.parametrize("multipart", [False, True], ids=["single-item", "multipart"])
def test_pinned_async_identity_provenance_strict_tags_and_multipart(multipart):
    bank = "engineering-memory-contract-" + uuid4().hex
    root = f"/v1/default/banks/{bank}"
    document = "chatgpt:" + uuid4().hex
    tags = ["project:synthetic-orchard", "source:chatgpt"]
    metadata = {"contract": "synthetic", "source_id": document}
    original_time = "2026-01-01T00:00:00+00:00"
    base = os.environ.get("ENGINEERING_MEMORY_LIVE_STORE_URL", "http://127.0.0.1:8889")
    with httpx.Client(base_url=base, trust_env=False, timeout=30) as client:
        deadline = time.monotonic() + 240

        def request(method, path, **kwargs):
            remaining = deadline - time.monotonic()
            assert remaining > 0, "compatibility experiment deadline exceeded"
            response = client.request(method, path, timeout=min(30, remaining), **kwargs)
            assert response.is_success, f"engine HTTP {response.status_code}"
            return response.json()

        def wait(operation):
            while True:
                result = request("GET", root + "/operations/" + operation)
                if result["status"] == "completed":
                    return result
                assert result["status"] in {"pending", "processing"}, "extraction failed"
                time.sleep(0.5)

        def item(content, mode):
            return {
                "content": content,
                "document_id": document,
                "timestamp": original_time,
                "metadata": metadata,
                "tags": tags,
                "update_mode": mode,
            }

        def recall(scope):
            return request(
                "POST",
                root + "/memories/recall",
                json={
                    "query": "What are the synthetic Orchard Observatory codename and port?",
                    "types": ["world", "experience"],
                    "tags": scope,
                    "tags_match": "all_strict",
                    "budget": "low",
                },
            )["results"]

        request("GET", "/health/ready")
        schema = request("GET", "/openapi.json")
        assert "/v1/default/banks/{bank_id}/memories" in schema["paths"]
        attempted = False
        try:
            operation = str(uuid4())
            body = {
                "async": True,
                "operation_id": operation,
                "items": [
                    item(
                        "The synthetic Orchard Observatory codename is cobalt-orchard.", "replace"
                    ),
                    item(" The synthetic Orchard Observatory uses port 47291.", "append"),
                ],
            }
            if not multipart:
                body["items"] = [
                    item(
                        "The synthetic Orchard Observatory codename is cobalt-orchard. "
                        "The synthetic Orchard Observatory uses port 47291.",
                        "replace",
                    )
                ]
            attempted = True
            accepted = request("POST", root + "/memories", json=body)
            assert accepted["operation_id"] == operation
            completed = wait(operation)
            replay = request("POST", root + "/memories", json=body)
            assert replay["operation_id"] == operation
            replayed = wait(operation)
            assert replayed["completed_at"] == completed["completed_at"]
            results = recall(tags)
            assert results, "no scoped facts returned"
            text = " ".join(fact["text"] for fact in results).lower()
            assert "cobalt-orchard" in text and "47291" in text
            for fact in results:
                assert fact["document_id"] == document
                assert fact["metadata"] == metadata
                assert set(tags) <= set(fact["tags"])
                assert fact["mentioned_at"].startswith("2026-01-01")
            assert recall(["project:unrelated-synthetic"]) == []
            replacement = str(uuid4())
            request(
                "POST",
                root + "/memories",
                json={
                    "async": True,
                    "operation_id": replacement,
                    "items": [
                        item(
                            "The synthetic Orchard Observatory codename is amber-valley.", "replace"
                        )
                    ],
                },
            )
            wait(replacement)
            refreshed = " ".join(fact["text"] for fact in recall(tags)).lower()
            assert "amber-valley" in refreshed
            assert "cobalt-orchard" not in refreshed and "47291" not in refreshed
        finally:
            if attempted:
                response = client.delete(root, timeout=15)
                assert response.status_code in {200, 204, 404}, "scratch-bank cleanup failed"
