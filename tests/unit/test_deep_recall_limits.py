from unittest.mock import Mock

import pytest

from engineering_memory.access.service import MemoryAccess
from engineering_memory.normalization import Source
from tests.unit.test_deep_recall import record


@pytest.mark.parametrize("limit", ["archive_limit", "page_limit", "evidence_limit"])
def test_coverage_describes_which_budget_stopped_work(limit):
    first = record(Source.CODEX, "first", "é" * 30000 if limit == "evidence_limit" else "Policy.")
    if limit == "page_limit":
        conversation = first.conversation
        first = first.model_copy(
            update={
                "conversation": conversation.model_copy(
                    update={"messages": conversation.messages * 51}
                )
            }
        )
    records = [first]
    if limit == "archive_limit":
        records.extend(record(Source.CODEX, f"extra-{i}", "Policy.") for i in range(7))
    memory, archive, synthesis = Mock(), Mock(), Mock()
    memory.recall.return_value = records
    archive.load.side_effect = {row.document_id: row for row in records}.__getitem__
    synthesis.synthesize.return_value = {
        "timeline": [{"text": "A policy was recorded.", "citations": [{"selector": "1"}]}]
    }
    outcome = MemoryAccess(memory, archive, synthesis=synthesis).deep_recall(
        project="demo", query="Policy"
    )
    assert outcome["status"] == "partial"
    coverage = outcome["coverage"]
    assert limit in coverage["limits"]
    assert coverage["archive_loads"] <= 6
    assert coverage["pages"] <= 12
    assert coverage["evidence_bytes"] <= 48 * 1024


def test_provider_size_cap_is_visible():
    from engineering_memory.access.deep_recall import SynthesisLimit

    row = record(Source.CODEX, "first", "Policy.")
    memory, archive, synthesis = Mock(), Mock(), Mock()
    memory.recall.return_value = [row]
    archive.load.return_value = row
    synthesis.synthesize.side_effect = SynthesisLimit("synthesis_response_limit")
    outcome = MemoryAccess(memory, archive, synthesis=synthesis).deep_recall(
        project="demo", query="Policy"
    )
    assert outcome["status"] == "verification_failed"
    assert outcome["timeline"] == []
    assert outcome["coverage"]["limits"] == ["synthesis_response_limit"]
