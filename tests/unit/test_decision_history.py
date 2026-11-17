"""Decision history must preserve action evidence, ordering and scope."""

from datetime import timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engineering_memory.access.deep_recall import SynthesisLimit
from engineering_memory.access.service import AccessError, MemoryAccess
from engineering_memory.normalization import ProjectTag, Source
from tests.unit.test_deep_recall import record


def event(kind, selector, version="Daily caching", **fields):
    return {"kind": kind, "version": version, "action": {"selector": selector}, **fields}


@pytest.fixture
def history():
    texts = [
        "Propose daily caching",
        "Adopt daily caching",
        "Revise daily caching",
        "Replace daily caching with hourly caching to reduce staleness",
    ]
    records = {
        str(index): record(Source.CODEX, str(index), text, days=index)
        for index, text in enumerate(texts, 1)
    }
    memory, archive, synthesis = Mock(), Mock(), Mock()
    memory.recall.side_effect = lambda *_: [
        SimpleNamespace(provenance=row.provenance) for row in records.values()
    ]
    archive.load.side_effect = lambda document_id: records[document_id.split(":")[1]]
    return MemoryAccess(memory, archive, synthesis=synthesis), records, memory, archive, synthesis


def lookup(history):
    return history[0].decision_history(project="demo", query="caching")


def test_orders_cross_session_lifecycle_by_action_time(history):
    _, records, memory, archive, synthesis = history
    records["foreign"] = record(Source.CODEX, "foreign", "Private", project="other")
    synthesis.synthesize_decisions.return_value = {
        "events": [
            event(
                "supersession",
                "4",
                "Hourly caching",
                prior_version="Daily caching",
                reason="Reduce staleness",
                context=[{"selector": "2"}],
            ),
            event("revision", "3"),
            event("adoption", "2", context=[{"selector": "1"}]),
            event("proposal", "1"),
        ]
    }
    result = lookup(history)
    assert result["status"] == "partial"
    assert [row["kind"] for row in result["events"]] == [
        "proposal",
        "adoption",
        "revision",
        "supersession",
    ]
    adoption, replacement = result["events"][1], result["events"][-1]
    assert adoption["occurred_at"] == records["2"].conversation.messages[0].sent_at.isoformat()
    assert replacement["prior_version"] == "Daily caching"
    assert replacement["version"] == "Hourly caching"
    assert replacement["reason"] == "Reduce staleness"
    assert replacement["action"]["document_id"] == "codex:4"
    assert "Private" not in str(synthesis.synthesize_decisions.call_args)
    assert all(args.args[1] == (ProjectTag(value="demo"),) for args in memory.recall.call_args_list)
    archive.load_original.assert_not_called()


def test_preserves_unknown_disputed_ties_and_separately_cited_conflicts(history):
    _, records, _, _, synthesis = history
    tied_at = records["1"].conversation.messages[0].sent_at.astimezone(timezone(timedelta(hours=2)))
    for key, timestamp in (("2", tied_at), ("3", None)):
        row = records[key]
        message = row.conversation.messages[0].model_copy(update={"sent_at": timestamp})
        records[key] = row.model_copy(
            update={"conversation": row.conversation.model_copy(update={"messages": (message,)})}
        )
    synthesis.synthesize_decisions.return_value = {
        "events": [
            event("proposal", "1"),
            event("adoption", "2"),
            event("revision", "3"),
            event("revision", "4", chronology_disputed=True),
        ],
        "conflicts": [
            {
                "summary": "The rollout is disputed",
                "accounts": [
                    {"text": "Daily", "citations": [{"selector": "2"}]},
                    {"text": "Hourly", "citations": [{"selector": "4"}]},
                ],
            }
        ],
    }
    result = lookup(history)
    assert result["status"] == "partial"
    assert [row["chronology"] for row in result["events"]] == [
        "known",
        "known",
        "unknown",
        "disputed",
    ]
    assert all(row["ordering_uncertain"] for row in result["events"][:2])
    assert all(row["occurred_at"] is None for row in result["events"][2:])
    assert result["events"][-1]["action"]["timestamp"] is not None
    accounts = result["conflicts"][0]["accounts"]
    assert [account["citations"][0]["document_id"] for account in accounts] == [
        "codex:2",
        "codex:4",
    ]


@pytest.mark.parametrize(
    "bad_event",
    [
        event("adoption", "999"),
        event("adoption", "1", occurred_at="2099-01-01"),
        event("supersession", "4"),
        event(
            "supersession",
            "4",
            "Hourly caching",
            prior_version="Daily caching",
            reason="Cut the cloud bill",
            context=[{"selector": "2"}],
        ),
        event("supersession", "4", prior_version="Weekly caching", context=[{"selector": "3"}]),
        event("revision", "1") | {"action": {"selector": "1", "quote": "Fabrication"}},
    ],
)
def test_fails_closed_for_bad_draft(history, bad_event):
    history[-1].synthesize_decisions.return_value = {"events": [event("proposal", "1"), bad_event]}
    result = lookup(history)
    assert (result["status"], result["events"], result["conflicts"]) == (
        "verification_failed",
        [],
        [],
    )


def test_no_synthesis_for_empty_or_mismatched_archive(history):
    _, _, _, archive, synthesis = history
    row = record(Source.CODEX, "wrong", "Different archive identity", project="other")
    archive.load.side_effect = None
    archive.load.return_value = row
    result = lookup(history)
    assert result["status"] == "insufficient_evidence"
    assert result["coverage"]["skipped"] == {"archive_mismatch": 4}
    synthesis.synthesize_decisions.assert_not_called()


def test_synthesis_limit_leaves_no_timeline(history):
    history[-1].synthesize_decisions.side_effect = SynthesisLimit("synthesis_timeout")
    result = lookup(history)
    assert result["status"] == "verification_failed"
    assert "synthesis_timeout" in result["coverage"]["limits"]


def test_deduplicates_events_and_retains_conflict_only_results(history):
    synthesis = history[-1]
    proposal = event("proposal", "1")
    synthesis.synthesize_decisions.return_value = {
        "events": [proposal, proposal | {"action": {"selector": "1", "quote": "daily caching"}}]
    }
    assert len(lookup(history)["events"]) == 1
    synthesis.synthesize_decisions.return_value = {
        "events": [],
        "conflicts": [
            {
                "summary": "Rollout disputed",
                "accounts": [
                    {"text": "Daily", "citations": [{"selector": "2"}]},
                    {"text": "Hourly", "citations": [{"selector": "4"}]},
                ],
            }
        ],
    }
    result = lookup(history)
    assert result["status"] == "partial"
    assert len(result["conflicts"]) == 1


@pytest.mark.parametrize("project", ["unknown", "unclassified", "demo*"])
def test_scope_is_required_before_retrieval(history, project):
    with pytest.raises(AccessError, match="invalid_input"):
        history[0].decision_history(project=project, query="caching")
    history[2].recall.assert_not_called()


def test_decision_synthesis_uses_configured_transport_and_selector_input():
    import json

    import httpx

    from engineering_memory.access.synthesis import OpenAICompatibleSynthesizer
    from engineering_memory.settings import DeepRecallSettings

    def respond(request):
        assert request.url == "https://example.test/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert "supersession" in body["messages"][0]["content"]
        assert json.loads(body["messages"][1]["content"]) == {
            "question": "Caching",
            "passages": [{"selector": "1", "text": "Adopt caching", "timestamp": None}],
        }
        return httpx.Response(
            200, json={"choices": [{"message": {"content": '{"events":[],"conflicts":[]}'}}]}
        )

    synthesis = OpenAICompatibleSynthesizer(
        DeepRecallSettings(base_url="https://example.test/v1", model="test-model"),
        transport=httpx.MockTransport(respond),
    )
    assert synthesis.synthesize_decisions("Caching", {"1": "Adopt caching"}, {"1": None}) == {
        "events": [],
        "conflicts": [],
    }


def test_single_message_can_establish_prior_version_and_supersession(history):
    history[-1].synthesize_decisions.return_value = {
        "events": [event("supersession", "4", "Hourly caching", prior_version="Daily caching")]
    }
    result = lookup(history)
    assert result["status"] == "completed"
    assert result["events"][0]["action"]["document_id"] == "codex:4"
    assert result["events"][0]["prior_version"] == "Daily caching"
