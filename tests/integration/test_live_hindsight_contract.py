"""Executable ARCHITECTURE §6/9/10 contracts against the pinned real engine.

Only the extraction dependency is synthetic. Use the isolated contract stack.
"""

import os
import time
from uuid import uuid4

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("ENGINEERING_MEMORY_LIVE_CONTRACT") != "1",
    reason="requires isolated live contract stack",
)


@pytest.fixture
def engine():
    url = os.environ.get("ENGINEERING_MEMORY_LIVE_STORE_URL", "http://127.0.0.1:8889")
    bank = "synthetic-contract-" + uuid4().hex
    with httpx.Client(base_url=url, timeout=30, trust_env=False) as client:
        root = f"/v1/default/banks/{bank}"
        yield client, root
        response = client.delete(root)
        assert response.status_code in {200, 204, 404}, "§9 scratch-bank cleanup failed"


@pytest.fixture
def llm():
    url = os.environ.get("CONTRACT_FIXTURE_URL", "http://127.0.0.1:8890")
    with httpx.Client(base_url=url, timeout=30, trust_env=False) as client:
        yield client
        client.post("/release").raise_for_status()
        assert client.get("/stats").json()["errors"] == 0, "§9 unexpected extraction protocol"


def request(engine, method, suffix, **kwargs):
    client, root = engine
    response = client.request(method, root + suffix, **kwargs)
    assert response.is_success, f"§6/9/10 {method} {suffix}: HTTP {response.status_code}"
    return response.json()


def item(name, text, tags=None, timestamp="2020-01-02T00:00:00Z"):
    return {
        "document_id": "chatgpt:" + name,
        "content": "Synthetic contract fact: " + text,
        "timestamp": timestamp,
        "tags": tags or [],
    }


def wait_until(predicate, seconds=90):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.2)
    pytest.fail("§9 live contract deadline exceeded")


def complete(engine, operation):
    def poll():
        result = request(engine, "GET", "/operations/" + operation)
        assert result["status"] in {"pending", "processing", "completed"}, "§9 extraction failed"
        return result if result["status"] == "completed" else None

    return wait_until(poll)


def retain(engine, items):
    operation = str(uuid4())
    request(
        engine, "POST", "/memories", json={"async": True, "operation_id": operation, "items": items}
    )
    return complete(engine, operation)


def recall(engine, **kwargs):
    return request(
        engine,
        "POST",
        "/memories/recall",
        json={
            "query": "Orchard",
            "types": ["world"],
            "budget": "high",
            "max_tokens": 10000,
            **kwargs,
        },
    )


def ids(results):
    return {fact["document_id"] for fact in results}


def test_default_replace_preserves_stable_identity(engine, llm):
    """§9/10: omitted update_mode replaces, with no stale facts or duplicate document."""
    retain(engine, [item("stable", "Orchard uses cobalt.")])
    first = recall(engine)["results"]
    assert ids(first) == {"chatgpt:stable"}, "§10 original identity missing"
    assert "cobalt" in str(first), "§9 positive control missing"
    retain(engine, [item("stable", "Orchard uses amber.")])
    results = recall(engine)["results"]
    assert ids(results) == {"chatgpt:stable"}, "§10 replacement identity changed"
    assert "amber" in str(results) and "cobalt" not in str(results), "§9 stale replacement facts"
    documents = request(engine, "GET", "/documents")["items"]
    assert len(documents) == 1, "§9/10 duplicate document after upsert"


def test_async_retry_does_not_extract_twice(engine, llm):
    """§9: replay while processing and after completion is extraction-free."""
    before = llm.get("/stats").json()["calls"]
    llm.post("/hold").raise_for_status()
    operation = str(uuid4())
    body = {
        "async": True,
        "operation_id": operation,
        "items": [item("retry", "Orchard uses cobalt.")],
    }
    accepted = request(engine, "POST", "/memories", json=body)
    assert accepted["operation_id"] == operation, "§9 operation id changed"
    wait_until(lambda: llm.get("/stats").json()["calls"] == before + 1)
    replay = request(engine, "POST", "/memories", json=body)
    assert replay["operation_id"] == operation, "§9 pending replay enqueued another operation"
    llm.post("/release").raise_for_status()
    completed = complete(engine, operation)
    initial = recall(engine)["results"]
    assert ids(initial) == {"chatgpt:retry"} and "cobalt" in str(initial), (
        "§9 retry positive control"
    )
    inventory = request(engine, "GET", "/documents")["items"]
    assert len(inventory) == 1, "§9 retry document positive control"
    request(engine, "POST", "/memories", json=body)
    repeated = complete(engine, operation)
    assert repeated["completed_at"] == completed["completed_at"], "§9 replay reprocessed operation"
    assert llm.get("/stats").json()["calls"] == before + 1, "§9 replay repeated extraction"
    assert {f["id"] for f in recall(engine)["results"]} == {f["id"] for f in initial}, (
        "§9 duplicated facts"
    )
    assert request(engine, "GET", "/documents")["items"] == inventory, "§9 replay changed documents"
    retain(engine, [item("counter-control", "Orchard uses amber.")])
    assert llm.get("/stats").json()["calls"] == before + 2, (
        "§9 extraction counter cannot detect work"
    )


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("any", {"ab", "a", "b", "abc", "none"}),
        ("all", {"ab", "abc", "none"}),
        ("any_strict", {"ab", "a", "b", "abc"}),
        ("all_strict", {"ab", "abc"}),
        ("exact", {"ab"}),
    ],
)
def test_tag_membership(engine, llm, mode, expected):
    """§6: exact identity membership including overlap, disjoint and global facts."""
    scopes = {
        "ab": ["project:a", "source:chatgpt"],
        "a": ["project:a"],
        "b": ["source:chatgpt"],
        "abc": ["project:a", "source:chatgpt", "type:conversation"],
        "other": ["project:other"],
        "none": [],
    }
    retain(engine, [item(name, f"Orchard uses {name}.", tags) for name, tags in scopes.items()])
    assert ids(recall(engine)["results"]) == {"chatgpt:" + name for name in scopes}, (
        "§6 positive control"
    )
    result = recall(engine, tags=["project:a", "source:chatgpt"], tags_match=mode)
    assert ids(result["results"]) == {"chatgpt:" + name for name in expected}, (
        f"§6 {mode} membership"
    )
    assert ids(recall(engine, tags=[], tags_match="exact")["results"]) == {"chatgpt:none"}, (
        "§6 empty exact scope"
    )


def test_original_timestamps_drive_temporal_retrieval(engine, llm):
    """§9: temporal arm selects original dates, independently of ingestion order."""
    retain(engine, [item("new", "Orchard uses amber.", timestamp="2024-06-01T00:00:00Z")])
    retain(engine, [item("old", "Orchard uses cobalt.", timestamp="2020-01-02T00:00:00Z")])
    for start, end, name in [
        ("2020-01-01", "2020-01-03", "old"),
        ("2024-05-31", "2024-06-02", "new"),
    ]:
        result = recall(
            engine,
            trace=True,
            temporal_window={"start": start + "T00:00:00Z", "end": end + "T00:00:00Z"},
        )
        dates = {f["document_id"]: f["mentioned_at"] for f in result["results"]}
        assert dates["chatgpt:old"].startswith("2020-01-02"), "§9 original timestamp lost"
        assert dates["chatgpt:new"].startswith("2024-06-01"), "§9 import time substituted"
        selected = {f["id"] for f in result["results"] if f["document_id"] == "chatgpt:" + name}
        temporal = [
            r for r in result["trace"]["retrieval_results"] if r["method_name"] == "temporal"
        ]
        # Temporal spreading can include out-of-window neighbours. The centred
        # in-window fact must lead this arm, independently of semantic reranking.
        ranked = [f for r in temporal for f in r["results"]]
        assert selected and ranked and ranked[0]["node_id"] in selected, (
            "§9 temporal arm did not prioritize the original date window"
        )


def test_never_written_bank_read_is_404(engine):
    """§9: recall does not create a never-written bank."""
    client, root = engine
    response = client.post(root + "/memories/recall", json={"query": "Orchard"})
    assert response.status_code == 404, "§9 read unexpectedly created a bank"
    assert client.get(root + "/config").status_code == 404, "§9 read provisioned bank"
