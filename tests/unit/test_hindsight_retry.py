"""Recovery, timing and privacy behavior of the concrete adapter."""

import json
from contextlib import suppress

import httpx
import pytest
import structlog

from engineering_memory.memory.hindsight.store import HindsightStore
from engineering_memory.memory.interface import MemoryStoreRejected, MemoryStoreUnavailable
from engineering_memory.settings import HindsightSettings
from tests.unit.test_hindsight_store import sample


@pytest.fixture
def timing(monkeypatch):
    from engineering_memory.memory.hindsight import store

    now = [100.0]
    sleeps = []
    monkeypatch.setattr(store.time, "monotonic", lambda: now[0])

    def sleep(delay):
        sleeps.append(float(delay))
        now[0] += delay

    monkeypatch.setattr(store.time, "sleep", sleep)
    return now, sleeps


def make(handler, **kwargs):
    return HindsightStore(
        HindsightSettings(base_url="http://engine.invalid"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        poll_interval=0,
        **kwargs,
    )


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_retain_recovers_with_identical_payload_and_growing_delays(status, timing):
    bodies = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"status": "completed"})
        bodies.append(request.content)
        if len(bodies) < 4:
            return httpx.Response(status)
        return httpx.Response(
            200,
            json={
                "success": True,
                "async": True,
                "operation_id": json.loads(request.content)["operation_id"],
            },
        )

    make(handler).retain(sample())
    assert len(bodies) == 4 and len(set(bodies)) == 1
    assert all(
        low <= delay <= high
        for delay, low, high in zip(timing[1], [1, 2, 4], [2, 3, 5], strict=True)
    )


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ReadTimeout,
        httpx.ConnectTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
        ConnectionResetError,
    ],
)
def test_recall_recovers_from_timeouts_and_resets(failure, timing):
    calls = []

    def handler(request):
        calls.append(request.content)
        if len(calls) == 1:
            if failure is ConnectionResetError:
                raise httpx.ReadError("PRIVATE") from ConnectionResetError(10054, "PRIVATE")
            raise failure("PRIVATE")
        return httpx.Response(200, json={"results": []})

    assert make(handler).recall("PRIVATE query") == ()
    assert len(calls) == 2 and calls[0] == calls[1]


def test_poll_retry_does_not_resubmit_retain(timing):
    methods = []

    def handler(request):
        methods.append(request.method)
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "async": True,
                    "operation_id": json.loads(request.content)["operation_id"],
                },
            )
        if methods.count("GET") == 1:
            raise httpx.ReadTimeout("PRIVATE")
        return httpx.Response(200, json={"status": "completed"})

    make(handler).retain(sample())
    assert methods == ["POST", "GET", "GET"]


@pytest.mark.parametrize("status", [400, 401, 403, 409, 422, 500])
def test_permanent_status_is_one_attempt(status, timing):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="PRIVATE")

    with pytest.raises(MemoryStoreRejected):
        make(handler).recall("PRIVATE")
    assert len(calls) == 1 and timing[1] == []


def test_exhaustion_preserves_identity_for_next_call(timing):
    bodies = []

    def handler(request):
        bodies.append(request.content)
        return httpx.Response(503)

    store = make(handler)
    for _ in range(2):
        with pytest.raises(MemoryStoreUnavailable):
            store.retain(sample())
    assert len(bodies) == 8 and len(set(bodies)) == 1
    assert len(timing[1]) == 6


def test_delay_cannot_cross_deadline(timing):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    with pytest.raises(MemoryStoreUnavailable):
        make(handler, request_timeout=0.5).recall("query")
    assert len(calls) == 1 and timing[1] == []


def test_clock_is_checked_after_sleep(timing):
    calls = []

    def handler(request):
        calls.append(request)
        timing[0][0] += 29
        return httpx.Response(503)

    with pytest.raises(MemoryStoreUnavailable):
        make(handler).recall("query")
    assert len(calls) == 1


def test_non_reset_network_error_is_not_retried(timing):
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectError("PRIVATE")

    with pytest.raises(MemoryStoreUnavailable):
        make(handler).recall("query")
    assert len(calls) == 1 and timing[1] == []


@pytest.mark.parametrize("outcome", ["success", "rejected", "exhausted"])
def test_structured_outcomes_exclude_private_values(outcome, timing):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("PRIVATE exception")
        if outcome == "success":
            return httpx.Response(200, json={"results": []})
        return httpx.Response(401 if outcome == "rejected" else 503, text="PRIVATE body")

    with (
        structlog.testing.capture_logs() as events,
        suppress(MemoryStoreRejected, MemoryStoreUnavailable),
    ):
        make(handler).recall("PRIVATE query")
    attempts = [event for event in events if event["event"] == "memory_request_attempt"]
    terminal = [event for event in events if event["event"] == "memory_request_finished"]
    assert [event["attempt"] for event in attempts] == list(range(1, len(calls) + 1))
    assert len(terminal) == 1 and terminal[0]["outcome"] == outcome
    assert terminal[0]["attempts"] == len(calls)
    assert "PRIVATE" not in json.dumps(events)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_attempts": 0},
        {"max_attempts": True},
        {"initial": 0},
        {"initial": float("nan")},
        {"maximum": 0.5},
        {"jitter": -1},
        {"jitter": float("inf")},
    ],
)
def test_invalid_policy_rejected_before_io(kwargs):
    from engineering_memory.memory.hindsight.retry import RetryPolicy

    with pytest.raises(ValueError):
        RetryPolicy(**kwargs)


def test_retry_checks_deadline_again_after_oversleep(timing, monkeypatch):
    from engineering_memory.memory.hindsight import store

    calls = []
    monkeypatch.setattr(store.time, "sleep", lambda delay: timing[0].__setitem__(0, 131))

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    with pytest.raises(MemoryStoreUnavailable):
        make(handler).recall("query")
    assert len(calls) == 1


def test_owned_async_transport_recovers(monkeypatch):
    clients = []
    calls = []
    original = httpx.AsyncClient

    async def handler(request):
        calls.append(request.content)
        if len(calls) < 2:
            return httpx.Response(503)
        return httpx.Response(200, json={"results": []})

    def factory(**kwargs):
        client = original(transport=httpx.MockTransport(handler), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    with HindsightStore(HindsightSettings(base_url="http://engine.invalid")) as store:
        assert store.recall("query") == ()
    assert len(calls) == 2 and calls[0] == calls[1]
    assert all(client.is_closed for client in clients)


def test_transient_then_permanent_stops_immediately(timing):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) == 1 else 400)

    with pytest.raises(MemoryStoreRejected):
        make(handler).recall("query")
    assert len(calls) == 2 and len(timing[1]) == 1


def test_malformed_success_is_not_retried(timing):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, text="PRIVATE malformed")

    with pytest.raises(MemoryStoreRejected):
        make(handler).recall("query")
    assert len(calls) == 1 and timing[1] == []


def test_retain_events_correlate_submission_and_poll(timing):
    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"status": "completed"})
        return httpx.Response(
            200,
            json={
                "success": True,
                "async": True,
                "operation_id": json.loads(request.content)["operation_id"],
            },
        )

    enriched = sample()
    with structlog.testing.capture_logs() as events:
        make(handler).retain(enriched)
    attempts = [event for event in events if event["event"] == "memory_request_attempt"]
    assert len(attempts) == 2
    assert attempts[0]["operation_id"] == attempts[1]["operation_id"]
    assert all(event["document_id"] == enriched.document_id for event in attempts)


def test_retain_submission_and_poll_share_deadline(timing):
    methods = []

    def handler(request):
        methods.append(request.method)
        if request.method == "POST":
            timing[0][0] += 239.5
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "async": True,
                    "operation_id": json.loads(request.content)["operation_id"],
                },
            )
        return httpx.Response(503)

    with pytest.raises(MemoryStoreUnavailable):
        make(handler).retain(sample())
    assert methods == ["POST", "GET"] and timing[1] == []


def test_delay_is_capped_and_not_slept_after_last_attempt(timing):
    from engineering_memory.memory.hindsight.retry import RetryPolicy

    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    policy = RetryPolicy(max_attempts=6)
    with pytest.raises(MemoryStoreUnavailable):
        make(handler, retry_policy=policy, request_timeout=200).recall("query")
    assert len(calls) == 6 and len(timing[1]) == 5
    assert timing[1][-2:] == [8, 8]


def test_uncertain_attempt_then_refusal_preserves_identity_on_later_call(timing):
    bodies = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"status": "completed"})
        bodies.append(request.content)
        if len(bodies) == 1:
            raise httpx.ReadTimeout("acknowledgement lost")
        if len(bodies) == 2:
            return httpx.Response(401)
        return httpx.Response(
            200,
            json={
                "success": True,
                "async": True,
                "operation_id": json.loads(request.content)["operation_id"],
            },
        )

    store = make(handler)
    with pytest.raises(MemoryStoreRejected):
        store.retain(sample())
    store.retain(sample())
    assert len(bodies) == 3 and len(set(bodies)) == 1
