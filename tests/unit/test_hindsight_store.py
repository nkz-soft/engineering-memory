"""Wire and failure tests for the concrete memory boundary."""

import json

import httpx
import pytest

from engineering_memory.memory.hindsight.store import HindsightStore
from engineering_memory.memory.interface import MemoryStoreRejected, MemoryStoreUnavailable
from engineering_memory.normalization import ProjectTag
from engineering_memory.settings import HindsightSettings
from tests.contracts import conversations


def make_store(handler, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HindsightStore(
        HindsightSettings(base_url="http://engine.invalid"),
        client=client,
        poll_interval=0,
        **kwargs,
    )


def sample(text="The observatory chose cobalt. 🌿"):
    return conversations.enrich(conversations.conversation(text=text))


def test_delivery_carries_full_ordered_context_identity_time_and_provenance():
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"status": "completed", "operation_id": operation[0]})
        payload = json.loads(request.content)
        operation.append(payload["operation_id"])
        return httpx.Response(
            200, json={"success": True, "async": True, "operation_id": operation[0]}
        )

    operation = []
    enriched = sample()
    make_store(handler).retain(enriched)
    body = json.loads(calls[0].content)
    assert calls[0].url.path.endswith("/memories")
    assert body["async"] is True
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["document_id"] == enriched.document_id
    assert item["timestamp"] == enriched.conversation.started_at.isoformat()
    assert item["update_mode"] == "replace"
    decoded = json.loads(item["content"])
    assert decoded == enriched.conversation.model_dump(mode="json")
    assert json.loads(
        item["metadata"]["engineering_memory.provenance"]
    ) == enriched.provenance.model_dump(mode="json")


def test_uncertain_retry_reuses_uuid_but_success_and_changed_payload_start_fresh():
    operations = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"status": "completed"})
        body = json.loads(request.content)
        operations.append(body["operation_id"])
        if len(operations) == 1:
            raise httpx.ReadTimeout("private payload and credential", request=request)
        return httpx.Response(
            200, json={"success": True, "async": True, "operation_id": operations[-1]}
        )

    store = make_store(handler)
    with pytest.raises(MemoryStoreUnavailable, match="unavailable"):
        store.retain(sample())
    store.retain(sample())
    store.retain(sample())
    store.retain(sample("changed"))
    store.retain(sample())
    assert operations[0] == operations[1]
    assert len(set(operations[1:])) == 4


@pytest.mark.parametrize("status", [400, 401, 403, 409, 422, 500, 429, 502, 503, 504])
def test_safe_status_translation(status):
    store = make_store(lambda request: httpx.Response(status, text="secret response credential"))
    error = MemoryStoreUnavailable if status in {429, 502, 503, 504} else MemoryStoreRejected
    for call in (lambda: store.retain(sample()), lambda: store.recall("query")):
        with pytest.raises(error) as raised:
            call()
        assert "secret" not in str(raised.value)
        assert "engine.invalid" not in str(raised.value)


def test_recall_strict_scope_limit_and_typed_provenance():
    enriched = sample()

    def handler(request):
        body = json.loads(request.content)
        assert body["tags_match"] == "all_strict"
        assert body["tags"] == ["project:engineering-memory"]
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "text": text,
                        "document_id": enriched.document_id,
                        "metadata": {
                            "engineering_memory.version": "1",
                            "engineering_memory.provenance": enriched.provenance.model_dump_json(),
                        },
                        "tags": ["project:engineering-memory"],
                    }
                    for text in ("first", "second", "third")
                ]
            },
        )

    results = make_store(handler).recall("query", (ProjectTag(value="engineering-memory"),), 2)
    assert [result.content for result in results] == ["first", "second"]
    assert all(result.provenance == enriched.provenance for result in results)


@pytest.mark.parametrize(
    "payload", [{}, {"results": [{}]}, {"results": [{"text": "fact", "metadata": {}}]}]
)
def test_malformed_recall_is_rejected(payload):
    with pytest.raises(MemoryStoreRejected):
        make_store(lambda request: httpx.Response(200, json=payload)).recall("query")


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_limit_never_performs_io(limit):
    with pytest.raises(MemoryStoreRejected):
        make_store(lambda request: pytest.fail("unexpected I/O")).recall("query", limit=limit)


def test_size_limit_and_empty_content_are_rejected_before_io():
    store = make_store(lambda request: pytest.fail("unexpected I/O"), max_request_bytes=100)
    with pytest.raises(MemoryStoreRejected):
        store.retain(sample("🌿" * 100))
    with pytest.raises(MemoryStoreRejected):
        store.retain(sample(""))


def test_completion_deadline_does_not_claim_success():
    def handler(request):
        if request.method == "POST":
            body = json.loads(request.content)
            return httpx.Response(
                200, json={"success": True, "async": True, "operation_id": body["operation_id"]}
            )
        return httpx.Response(200, json={"status": "processing"})

    with pytest.raises(MemoryStoreUnavailable):
        make_store(handler, completion_timeout=0.01).retain(sample())


@pytest.mark.parametrize(
    "status", ["failed", "cancelled", "not_found", "unknown", [], {}, None, 42]
)
def test_unsuccessful_operation_is_never_success(status):
    def handler(request):
        if request.method == "POST":
            body = json.loads(request.content)
            return httpx.Response(
                200, json={"success": True, "async": True, "operation_id": body["operation_id"]}
            )
        return httpx.Response(200, json={"status": status})

    with pytest.raises((MemoryStoreRejected, MemoryStoreUnavailable)):
        make_store(handler).retain(sample())


def test_definitive_refusals_do_not_exhaust_uncertain_operation_capacity():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(401)

    store = make_store(handler)
    for index in range(130):
        enriched = conversations.enrich(conversations.conversation(str(index)))
        with pytest.raises(MemoryStoreRejected):
            store.retain(enriched)
    assert len(calls) == 130


def test_response_arriving_after_completion_deadline_is_not_success():
    import time

    def handler(request):
        time.sleep(0.02)
        body = json.loads(request.content)
        return httpx.Response(
            200, json={"success": True, "async": True, "operation_id": body["operation_id"]}
        )

    with pytest.raises(MemoryStoreUnavailable):
        make_store(handler, completion_timeout=0.01).retain(sample())


def test_owned_transport_cancels_at_deadline_and_closes_session(monkeypatch):
    import asyncio
    import time

    clients = []
    cancelled = []
    original = httpx.AsyncClient

    async def handler(request):
        try:
            await asyncio.sleep(5)
        finally:
            cancelled.append(True)
        return httpx.Response(200, json={"results": []})

    def factory(**kwargs):
        assert kwargs["trust_env"] is False
        assert kwargs["follow_redirects"] is False
        client = original(transport=httpx.MockTransport(handler), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    started = time.monotonic()
    with (
        HindsightStore(
            HindsightSettings(base_url="http://engine.invalid"), request_timeout=0.05
        ) as store,
        pytest.raises(MemoryStoreUnavailable),
    ):
        store.recall("query")
    assert time.monotonic() - started < 1
    assert cancelled
    assert all(client.is_closed for client in clients)


def test_injected_client_remains_caller_owned():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"results": []}))
    )
    with HindsightStore(
        HindsightSettings(base_url="http://engine.invalid"), client=client
    ) as store:
        assert store.recall("query") == ()
    assert not client.is_closed
    client.close()


@pytest.mark.parametrize(
    "ack",
    [
        {},
        {"success": True, "async": False},
        {"success": True, "async": True, "operation_id": "wrong"},
    ],
)
def test_invalid_acknowledgement_preserves_retry_identity(ack):
    operations = []

    def handler(request):
        operations.append(json.loads(request.content)["operation_id"])
        return httpx.Response(200, json=ack)

    store = make_store(handler)
    for _ in range(2):
        with pytest.raises(MemoryStoreRejected):
            store.retain(sample())
    assert operations[0] == operations[1]


def test_out_of_scope_engine_result_is_rejected():
    enriched = sample()
    fact = {
        "text": "fact",
        "document_id": enriched.document_id,
        "tags": [],
        "metadata": {
            "engineering_memory.version": "1",
            "engineering_memory.provenance": enriched.provenance.model_dump_json(),
        },
    }
    store = make_store(lambda request: httpx.Response(200, json={"results": [fact]}))
    with pytest.raises(MemoryStoreRejected):
        store.recall("query", (ProjectTag(value="engineering-memory"),))


def test_refused_replay_preserves_prior_uncertain_uuid():
    operations = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"status": "completed"})
        operations.append(json.loads(request.content)["operation_id"])
        if len(operations) == 1:
            raise httpx.ReadTimeout("uncertain", request=request)
        if len(operations) == 2:
            return httpx.Response(401)
        return httpx.Response(
            200, json={"success": True, "async": True, "operation_id": operations[-1]}
        )

    store = make_store(handler)
    with pytest.raises(MemoryStoreUnavailable):
        store.retain(sample())
    with pytest.raises(MemoryStoreRejected):
        store.retain(sample())
    store.retain(sample())
    assert len(set(operations)) == 1
