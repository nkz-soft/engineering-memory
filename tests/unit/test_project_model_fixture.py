"""The deterministic fixture drives tool use, not a replacement memory engine."""

import pytest


def test_fixture_rejects_deliberately_failed_synthesis():
    from tests.integration.hindsight_contract.llm import completion

    with pytest.raises(ValueError):
        completion(
            {
                "tools": [{"function": {"name": "recall"}}],
                "messages": [{"role": "user", "content": "FORCE_FIXTURE_FAILURE"}],
            }
        )


def test_fixture_uses_tool_evidence_for_document_and_citations():
    from tests.integration.hindsight_contract.llm import completion

    body = {
        "tools": [{"function": {"name": "done"}}],
        "tool_choice": {"type": "function", "function": {"name": "done"}},
        "messages": [
            {
                "role": "tool",
                "content": '{"results":[{"id":"fact-a","text":"Orchard uses amber gateway."}]}',
            }
        ],
    }
    call = completion(body)["tool_calls"][0]["function"]
    import json

    value = json.loads(call["arguments"])
    assert value["memory_ids"] == ["fact-a"]
    assert value["document"]["sections"][0]["blocks"] == ["Orchard uses amber gateway."]


def test_fixture_obeys_forced_recall_and_does_not_invent_evidence():
    import json

    from tests.integration.hindsight_contract.llm import completion

    body = {
        "tools": [{"function": {"name": "recall"}}],
        "tool_choice": {"type": "function", "function": {"name": "recall"}},
        "messages": [],
    }
    assert completion(body)["tool_calls"][0]["function"]["name"] == "recall"
    body["tool_choice"]["function"]["name"] = "done"
    result = completion(body)["tool_calls"][0]["function"]
    assert not json.loads(result["arguments"])["answer_found"]
