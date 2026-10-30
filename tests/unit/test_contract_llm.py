"""The test LLM must fail closed and count real extraction requests (§9)."""

import pytest

from tests.integration.hindsight_contract.llm import extraction


def payload(text="Synthetic contract fact: Orchard uses cobalt."):
    return {
        "model": "contract",
        "messages": [
            {"role": "system", "content": "Extract facts"},
            {"role": "user", "content": text},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "FactExtractionResponse",
                "schema": {"type": "object", "properties": {"facts": {"type": "array"}}},
            },
        },
    }


def test_extraction_preserves_only_synthetic_fact():
    result = extraction(payload())
    assert result["facts"][0]["what"] == "Orchard uses cobalt."
    assert result["facts"][0]["occurred_start"] is None


@pytest.mark.parametrize(
    "body",
    [{}, payload("private arbitrary content"), {**payload(), "response_format": {"type": "text"}}],
)
def test_unknown_protocol_or_content_fails_closed(body):
    with pytest.raises(ValueError, match="unsupported"):
        extraction(body)
