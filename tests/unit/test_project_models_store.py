"""Backend wire and fail-closed lineage contracts, synthetic evidence only."""

import json

import httpx
import pytest

from engineering_memory.memory.interface import MemoryStoreRejected, MemoryStoreUnavailable
from engineering_memory.settings import HindsightSettings
from tests.contracts import conversations as synth


def setup_store(handler, **options):
    from engineering_memory.memory.hindsight.project_models import HindsightProjectModels

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HindsightProjectModels(
        HindsightSettings(base_url="http://engine", bank_id="synthetic"),
        client=client,
        poll_interval=0,
        **options,
    )


def evidence():
    enriched = synth.enrich(synth.conversation_using_every_field())
    provenance = enriched.provenance.model_copy(update={"project": "alpha"})
    return {
        "id": "fact-1",
        "text": "A supported architecture",
        "type": "world",
        "state": "valid",
        "tags": ["project:alpha"],
        "document_id": enriched.document_id,
        "metadata": {
            "engineering_memory.version": "1",
            "engineering_memory.provenance": provenance.model_dump_json(),
        },
    }


def key_and_model():
    from engineering_memory.memory.hindsight.project_models import model_definition
    from engineering_memory.memory.interface.project_models import ProjectModelKey

    key = ProjectModelKey(project="alpha", kind="architecture")
    model = {
        **model_definition(key),
        "bank_id": "synthetic",
        "content": "A supported architecture",
        "last_refreshed_at": "2026-11-04T09:00:00Z",
        "is_stale": False,
        "last_refresh_failed_at": None,
        "reflect_response": {"based_on": {"world": [{"id": "fact-1"}]}},
    }
    return key, model


def test_missing_and_pending_never_generate():
    key, model = key_and_model()

    def handle(request):
        assert request.method == "GET"
        return httpx.Response(404)

    assert setup_store(handle).get_project_model(key).status == "missing"
    model.update(content=None, last_refreshed_at=None)
    assert (
        setup_store(lambda _: httpx.Response(200, json=model)).get_project_model(key).status
        == "pending"
    )


def test_read_resolves_fact_metadata_without_recall_or_writes():
    key, model = key_and_model()

    def handle(request):
        assert request.method == "GET"
        return httpx.Response(200, json=evidence() if "/memories/" in request.url.path else model)

    result = setup_store(handle).get_project_model(key)
    assert result.status == "ready"
    assert result.snapshot.content == "A supported architecture"
    assert result.snapshot.supports[0].provenance.project == "alpha"
    assert result.snapshot.supports[0].document_id == evidence()["document_id"]


@pytest.mark.parametrize(
    "mutation", ["foreign_tag", "foreign_provenance", "invalidated", "identity", "missing"]
)
def test_unsafe_fact_lineage_rejected(mutation):
    key, model = key_and_model()
    fact = evidence()
    if mutation == "foreign_tag":
        fact["tags"] = ["project:beta"]
    if mutation == "foreign_provenance":
        provenance = json.loads(fact["metadata"]["engineering_memory.provenance"])
        provenance["project"] = "beta"
        fact["metadata"]["engineering_memory.provenance"] = json.dumps(provenance)
    if mutation == "invalidated":
        fact["state"] = "invalidated"
    if mutation == "identity":
        fact["document_id"] = "chatgpt:wrong"

    def handle(request):
        if "/memories/" in request.url.path:
            return httpx.Response(404 if mutation == "missing" else 200, json=fact)
        return httpx.Response(200, json=model)

    with pytest.raises(MemoryStoreRejected):
        setup_store(handle).get_project_model(key)


def test_observation_resolves_each_source_and_deduplicates_documents():
    key, model = key_and_model()
    model["reflect_response"] = {"based_on": {"observation": [{"id": "obs-1"}]}}

    def handle(request):
        if request.url.path.endswith("/memories/obs-1"):
            return httpx.Response(
                200,
                json={
                    "id": "obs-1",
                    "type": "observation",
                    "state": "valid",
                    "tags": ["project:alpha"],
                    "source_memory_ids": ["fact-1", "fact-2"],
                },
            )
        if "/memories/" in request.url.path:
            return httpx.Response(
                200, json={**evidence(), "id": request.url.path.rsplit("/", 1)[1]}
            )
        return httpx.Response(200, json=model)

    assert len(setup_store(handle).get_project_model(key).snapshot.supports) == 1


@pytest.mark.parametrize(
    "mutation", ["scope", "query", "trigger", "unsupported", "empty", "naive_time"]
)
def test_untrusted_model_rejected(mutation):
    key, model = key_and_model()
    if mutation == "scope":
        model["tags"] = ["project:beta"]
    if mutation == "query":
        model["source_query"] = "foreign definition"
    if mutation == "trigger":
        model["trigger"]["tag_groups"] = [{"tags": ["project:beta"]}]
    if mutation == "unsupported":
        model["reflect_response"]["based_on"] = {"mental-models": [{"id": "other"}]}
    if mutation == "empty":
        model["reflect_response"]["based_on"] = {}
    if mutation == "naive_time":
        model["last_refreshed_at"] = "2026-11-04T09:00:00"
    with pytest.raises(MemoryStoreRejected):
        setup_store(lambda _: httpx.Response(200, json=model)).get_project_model(key)


def test_lineage_lookup_budget_and_safe_transport_failure():
    key, model = key_and_model()
    model["reflect_response"]["based_on"]["world"] = [{"id": str(i)} for i in range(129)]
    with pytest.raises(MemoryStoreRejected):
        setup_store(lambda _: httpx.Response(200, json=model)).get_project_model(key)

    def unavailable(_):
        raise httpx.ConnectError("PRIVATE_SENTINEL")

    with pytest.raises(MemoryStoreUnavailable) as error:
        setup_store(unavailable).get_project_model(key)
    assert "PRIVATE" not in str(error.value)


def test_create_then_refresh_keeps_identity_and_requires_completion():
    key, completed = key_and_model()
    state, writes = {}, []

    def handle(request):
        path = request.url.path
        if request.method == "POST":
            body = json.loads(request.content)
            writes.append((path, body))
            if path.endswith("/mental-models"):
                assert body["tags"] == ["project:alpha"]
                assert body["trigger"]["tags_match"] == "all_strict"
                assert body["trigger"]["exclude_mental_models"] is True
                assert not body["trigger"]["refresh_after_consolidation"]
                state["model"] = {**completed, "content": None, "last_refreshed_at": None}
                return httpx.Response(
                    200, json={"mental_model_id": body["id"], "operation_id": "op-1"}
                )
            assert body == {"mode": "full"}
            return httpx.Response(200, json={"operation_id": "op-2", "status": "queued"})
        if path.endswith("/operations"):
            return httpx.Response(200, json={"total": 0, "operations": []})
        if "/operations/" in path:
            state["model"] = completed
            return httpx.Response(
                200,
                json={
                    "operation_id": path.rsplit("/", 1)[1],
                    "operation_type": "refresh_mental_model",
                    "mental_model_id": completed["id"],
                    "status": "completed",
                },
            )
        if "/memories/" in path:
            return httpx.Response(200, json=evidence())
        return httpx.Response(200, json=state["model"]) if state else httpx.Response(404)

    store = setup_store(handle)
    assert store.refresh_project_model(key).status == "completed"
    assert store.refresh_project_model(key).status == "completed"
    assert [path.rsplit("/", 1)[1] for path, _ in writes] == ["mental-models", "refresh"]
    assert writes[1][0].split("/")[-2] == writes[0][1]["id"]


def test_running_operation_is_reconciled_before_fresh_refresh():
    key, model = key_and_model()
    finished, posts = [], []

    def handle(request):
        if request.method == "POST":
            assert finished == ["existing"]
            posts.append(request.url.path)
            return httpx.Response(200, json={"operation_id": "new", "status": "queued"})
        if request.url.path.endswith("/operations"):
            return httpx.Response(
                200,
                json={
                    "total": 1,
                    "operations": [
                        {
                            "id": "existing",
                            "mental_model_id": model["id"],
                            "task_type": "refresh_mental_model",
                            "status": "processing",
                        }
                    ],
                },
            )
        if "/operations/" in request.url.path:
            identity = request.url.path.rsplit("/", 1)[1]
            finished.append(identity)
            return httpx.Response(
                200,
                json={
                    "operation_id": identity,
                    "operation_type": "refresh_mental_model",
                    "mental_model_id": model["id"],
                    "status": "completed",
                },
            )
        return httpx.Response(200, json=evidence() if "/memories/" in request.url.path else model)

    assert setup_store(handle).refresh_project_model(key).status == "completed"
    assert finished == ["existing", "new"] and len(posts) == 1


@pytest.mark.parametrize(
    "status,want", [("failed", "failed"), ("processing", "pending"), ("not_found", "unavailable")]
)
def test_refresh_failure_timeout_and_missing_operation_are_not_success(status, want):
    key, model = key_and_model()
    posts = []

    def handle(request):
        if request.method == "POST":
            posts.append(request.url.path)
            return httpx.Response(200, json={"operation_id": "op", "status": "queued"})
        if request.url.path.endswith("/operations"):
            return httpx.Response(200, json={"total": 0, "operations": []})
        if "/operations/" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "operation_id": "op",
                    "operation_type": "refresh_mental_model",
                    "mental_model_id": model["id"],
                    "status": status,
                },
            )
        return httpx.Response(200, json=model)

    outcome = setup_store(handle, completion_timeout=0.03).refresh_project_model(key)
    assert outcome.status == want and outcome.refreshed_at is None
    assert len(posts) == 1


def test_uncertain_post_is_not_blindly_retried():
    key, model = key_and_model()
    posts = []

    def handle(request):
        if request.method == "POST":
            posts.append(request.url.path)
            raise httpx.ReadTimeout("PRIVATE")
        if request.url.path.endswith("/operations"):
            return httpx.Response(200, json={"total": 0, "operations": []})
        return httpx.Response(200, json=model)

    assert setup_store(handle).refresh_project_model(key).status == "unavailable"
    assert len(posts) == 1


def test_failed_first_generation_is_not_reported_pending():
    key, model = key_and_model()
    model.update(
        content=None, last_refreshed_at=None, last_refresh_failed_at="2026-11-04T09:00:00Z"
    )
    result = setup_store(lambda _: httpx.Response(200, json=model)).get_project_model(key)
    assert result.status == "failed" and result.last_refresh_failed_at is not None


def test_refresh_lock_wait_respects_total_deadline():
    import threading

    key, _ = key_and_model()

    def refuse(_):
        raise AssertionError("deadline-expired refresh contacted backend")

    store = setup_store(refuse, completion_timeout=0.03)
    finished = threading.Event()
    outcomes = []

    def refresh():
        outcomes.append(store.refresh_project_model(key))
        finished.set()

    store._lock.acquire()
    thread = threading.Thread(target=refresh)
    try:
        thread.start()
        assert finished.wait(0.15), "refresh waited beyond its total deadline"
    finally:
        store._lock.release()
        thread.join(1)
    assert outcomes[0].status == "unavailable"
