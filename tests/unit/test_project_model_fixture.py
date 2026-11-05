"""The deterministic fixture drives tool use, not a replacement memory engine."""

import json

import pytest

from tests.integration.hindsight_contract.llm import completion


def request(properties, messages):
    body = {
        "response_format": {"json_schema": {"schema": {"properties": properties}}},
        "messages": messages,
    }
    return json.loads(completion(body)["content"])


def test_fixture_rejects_deliberately_failed_synthesis():
    with pytest.raises(ValueError, match="deliberately failed synthetic synthesis"):
        request({"query": {}}, [{"role": "user", "content": "FORCE_FIXTURE_FAILURE"}])


def test_fixture_uses_tool_evidence_for_document_and_citations():
    value = request(
        {"markdown": {}},
        [
            {
                "role": "user",
                "content": 'Result of `recall`:\n{"results":[{"id":"f1",'
                '"text":"Orchard uses amber gateway."}]}',
            }
        ],
    )
    assert value["memory_ids"] == ["f1"]
    assert value["markdown"] == "## Project summary\n\n> Orchard uses amber gateway."


def test_fixture_obeys_forced_recall_and_does_not_invent_evidence():
    assert request({"query": {}}, [])["query"] == "Orchard"
    assert not request({"markdown": {}}, [])["answer_found"]

    call_schema = {"anyOf": [{"properties": {"name": {"enum": ["recall"]}}}]}
    value = request({"call": call_schema}, [])
    assert value["call"]["name"] == "recall"
    assert value["call"]["arguments"]["query"] == "Orchard"
