"""Mutation controls exercise the actual live assertions with wrong engine outcomes."""

from types import SimpleNamespace

import pytest

from tests.integration import test_live_hindsight_contract as live


@pytest.fixture(autouse=True)
def no_retain(monkeypatch):
    monkeypatch.setattr(live, "retain", lambda *a: None)


def fact(name, text="Orchard uses cobalt.", date="2020-01-02T00:00:00Z"):
    return {"id": name, "document_id": "chatgpt:" + name, "text": text, "mentioned_at": date}


@pytest.mark.parametrize("bad", ["stale", "duplicate"])
def test_replacement_assertions_reject_stale_or_duplicate(monkeypatch, bad):
    original = {"results": [fact("stable")]}
    changed = {
        "results": [fact("stable", "Orchard uses amber." + (" cobalt" if bad == "stale" else ""))]
    }
    responses = iter([original, changed])
    monkeypatch.setattr(live, "recall", lambda *a, **k: next(responses))
    monkeypatch.setattr(live, "request", lambda *a, **k: {"items": [{}, {}]})
    with pytest.raises(AssertionError, match="§9"):
        live.test_default_replace_preserves_stable_identity(None, None)


def test_retry_assertions_reject_extra_extraction(monkeypatch):
    counts = iter([0, 2])
    response = SimpleNamespace(raise_for_status=lambda: None)
    llm = SimpleNamespace(
        post=lambda *a: response,
        get=lambda *a: SimpleNamespace(json=lambda: {"calls": next(counts)}),
    )
    monkeypatch.setattr(live, "wait_until", lambda *a: True)
    monkeypatch.setattr(live, "complete", lambda *a: {"completed_at": "same"})
    monkeypatch.setattr(live, "recall", lambda *a: {"results": [fact("retry")]})

    def request(engine, method, path, **kwargs):
        return (
            {"items": [{}]}
            if path == "/documents"
            else {"operation_id": kwargs["json"]["operation_id"]}
        )

    monkeypatch.setattr(live, "request", request)
    with pytest.raises(AssertionError, match="repeated extraction"):
        live.test_async_retry_does_not_extract_twice(None, llm)


def test_tag_assertions_reject_scope_leak(monkeypatch):
    all_facts = [fact(name) for name in ["ab", "a", "b", "abc", "other", "none"]]
    monkeypatch.setattr(live, "recall", lambda *a, **k: {"results": all_facts})
    with pytest.raises(AssertionError, match="§6 exact membership"):
        live.test_tag_membership(None, None, "exact", {"ab"})


@pytest.mark.parametrize("bad", ["import-time", "ranking"])
def test_temporal_assertions_reject_import_time_or_wrong_priority(monkeypatch, bad):
    results = [
        fact("old", date="2026-10-30" if bad == "import-time" else "2020-01-02"),
        fact("new", date="2024-06-01"),
    ]
    monkeypatch.setattr(
        live,
        "recall",
        lambda *a, **k: {
            "results": results,
            "trace": {
                "retrieval_results": [
                    {"method_name": "temporal", "results": [{"node_id": "new"}, {"node_id": "old"}]}
                ]
            },
        },
    )
    with pytest.raises(AssertionError, match="§9"):
        live.test_original_timestamps_drive_temporal_retrieval(None, None)


def test_untouched_bank_assertion_rejects_successful_read():
    client = SimpleNamespace(post=lambda *a, **k: SimpleNamespace(status_code=200))
    with pytest.raises(AssertionError, match="§9 read unexpectedly"):
        live.test_never_written_bank_read_is_404((client, "/synthetic-bank"))
