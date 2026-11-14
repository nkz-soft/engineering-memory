"""Exercise the shared read path with hostile retrieval and synthesis outputs."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engineering_memory.access.service import AccessError, MemoryAccess
from engineering_memory.normalization import ProjectTag, Source
from tests.contracts import conversations as synth


def record(source, key, text, days=0, project="demo"):
    template = synth.conversation_using_every_field()
    when = template.started_at + timedelta(days=days)
    message = template.messages[0].model_copy(
        update={"text": text, "sent_at": when, "tool_activity": ()}
    )
    base = synth.enrich(
        template.model_copy(
            update={
                "source": source,
                "source_id": key,
                "started_at": when,
                "last_activity_at": when,
                "messages": (message,),
            }
        )
    )
    return base.model_copy(
        update={
            "provenance": base.provenance.model_copy(update={"project": project}),
            "tags": (ProjectTag(value=project),),
        }
    )


@pytest.fixture
def run():
    first = record(Source.CLAUDE_CODE, "a", "Proposed daily caching.")
    second = record(Source.CODEX, "b", "Switched to hourly caching.", days=1)
    foreign = record(Source.CODEX, "foreign", "Foreign evidence.", project="demo-extra")
    mismatch = record(Source.CODEX, "mismatch", "Wrong archive scope.")
    memory, archive, synthesis = Mock(), Mock(), Mock()
    memory.recall.return_value = [
        SimpleNamespace(provenance=row.provenance) for row in (second, foreign, first, mismatch)
    ]
    records = {r.document_id: r for r in (first, second, mismatch)}
    records[mismatch.document_id] = mismatch.model_copy(
        update={
            "tags": (ProjectTag(value="demo-extra"),),
            "provenance": mismatch.provenance.model_copy(update={"project": "demo-extra"}),
        }
    )
    archive.load.side_effect = records.__getitem__

    def answer(query, passages, times):
        assert list(passages.values()) == ["Switched to hourly caching.", "Proposed daily caching."]
        return {
            "timeline": [
                {"text": text, "citations": [{"selector": key}]} for key, text in passages.items()
            ]
        }

    synthesis.synthesize.side_effect = answer
    return MemoryAccess(memory, archive, synthesis=synthesis), memory, archive, synthesis


def test_scoped_timeline_and_distinct_loads(run):
    access, memory, archive, _ = run
    result = access.deep_recall(query="Why did we change caching?", project="demo")
    assert result["status"] == "partial"
    assert [row["citations"][0]["document_id"] for row in result["timeline"]] == [
        "claude-code:a",
        "codex:b",
    ]
    assert result["timeline"][0]["citations"][0]["message_index"] == 0
    assert result["timeline"][0]["citations"][0]["quote"] == "Proposed daily caching."
    assert len(memory.recall.call_args_list) == 3
    assert all(call.args[1] == (ProjectTag(value="demo"),) for call in memory.recall.call_args_list)
    assert [call.args[0] for call in archive.load.call_args_list] == [
        "codex:b",
        "claude-code:a",
        "codex:mismatch",
    ]
    archive.load_original.assert_not_called()
    assert result["coverage"]["skipped"] == {"foreign_hit": 3, "archive_mismatch": 1}


@pytest.mark.parametrize(
    "selector,quote", [("999", None), ("1", "Fabrication"), ("1", "Proposed daily caching.")]
)
def test_rejects_unobserved_anchors_and_bad_quotes(run, selector, quote):
    access, _, _, synthesis = run
    synthesis.synthesize.side_effect = None
    synthesis.synthesize.return_value = {
        "timeline": [
            {"text": "The policy changed.", "citations": [{"selector": selector, "quote": quote}]}
        ]
    }
    result = access.deep_recall(query="Caching changes", project="demo")
    assert result["status"] == "verification_failed"
    assert result["timeline"] == []


def test_no_evidence_never_calls_synthesizer(run):
    access, memory, _, synthesis = run
    memory.recall.return_value = []
    assert access.deep_recall(query="Caching", project="demo")["status"] == "insufficient_evidence"
    synthesis.synthesize.assert_not_called()


def test_bounded_hit_window(run):
    access, memory, archive, synthesis = run
    memory.recall.return_value *= 100
    synthesis.synthesize.side_effect = None
    synthesis.synthesize.return_value = {"timeline": []}
    result = access.deep_recall(query="Caching changes", project="demo")
    assert result["coverage"]["hits"] <= 30
    assert "hit_limit" in result["coverage"]["limits"]
    assert archive.load.call_count <= 6


@pytest.mark.parametrize("project", ["", "unclassified", "demo*"])
def test_explicit_classified_project(run, project):
    access, memory, _, _ = run
    with pytest.raises(AccessError, match="invalid_input"):
        access.deep_recall(query="Caching", project=project)
    memory.recall.assert_not_called()


@pytest.mark.parametrize(
    "text,uncertainty",
    [
        ("They said 'never expire'.", False),
        ("On 2099-01-01 the policy changed.", False),
        ("See hermes:unverified.", False),
        ("The policy changed.", "false"),
    ],
)
def test_rejects_unverified_narrative_and_malformed_uncertainty(run, text, uncertainty):
    access, _, _, synthesis = run
    synthesis.synthesize.side_effect = None
    synthesis.synthesize.return_value = {
        "timeline": [{"text": text, "citations": [{"selector": "1"}]}],
        "uncertainty": uncertainty,
    }
    result = access.deep_recall(query="Caching changes", project="demo")
    assert result["status"] == "verification_failed"
    assert not result["timeline"]
