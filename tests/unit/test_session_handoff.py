"""Session handoff uses a bounded manifest of the selected normalized archive."""

from unittest.mock import Mock

import pytest

from engineering_memory.access.service import AccessError, MemoryAccess
from engineering_memory.normalization import Source
from tests.unit.test_deep_recall import record


@pytest.fixture
def handoff():
    archive, memory, synthesis = Mock(), Mock(), Mock()
    archive.load.return_value = record(Source.CLAUDE_CODE, "one", "Goal: fix queue.")
    access = MemoryAccess(memory, archive, handoff_synthesis=synthesis)
    return access, archive, memory, synthesis


def test_handoff_uses_one_archive_and_escapes_generated_links(handoff):
    access, archive, memory, synthesis = handoff
    synthesis.synthesize_handoff.return_value = {
        "entries": [
            {
                "section": "goal",
                "status": "recorded",
                "text": "Fix queue [link](https://bad.test)",
                "selectors": ["1"],
            }
        ]
    }

    result = access.session_handoff(document_id="claude-code:one", project="demo")

    for heading in ("Goal", "Confirmed decisions", "Touched files", "Checks", "Open questions"):
        assert f"## {heading}" in result["markdown"]
    assert "https://bad.test" not in result["markdown"]
    assert "#view=session&project=demo&document=claude-code%3Aone&message=0" in result["markdown"]
    archive.load.assert_called_once_with("claude-code:one")
    assert not memory.mock_calls
    archive.load_original.assert_not_called()
    synthesis.synthesize_handoff.assert_called_once()


def test_wrong_scope_never_reaches_synthesis(handoff):
    access, _, _, synthesis = handoff
    with pytest.raises(AccessError, match="not_found"):
        access.session_handoff(document_id="claude-code:one", project="foreign")
    synthesis.synthesize_handoff.assert_not_called()


@pytest.mark.parametrize("section,selector", [("goal", "9"), ("checks", "1"), ("files", "1")])
def test_rejects_unobserved_selectors_and_unrecorded_outcomes(handoff, section, selector):
    access, _, _, synthesis = handoff
    synthesis.synthesize_handoff.return_value = {
        "entries": [
            {"section": section, "status": "recorded", "text": "Completed", "selectors": [selector]}
        ]
    }
    with pytest.raises(AccessError, match="synthesis_invalid"):
        access.session_handoff(document_id="claude-code:one", project="demo")


def test_partial_coverage_retains_original_late_positions(handoff):
    access, archive, _, synthesis = handoff
    item = archive.load.return_value
    first = item.conversation.messages[0]
    messages = (first,) * 399 + (first.model_copy(update={"text": "Late goal"}),)
    archive.load.return_value = item.model_copy(
        update={"conversation": item.conversation.model_copy(update={"messages": messages})}
    )

    def summarize(passages, times):
        assert len(passages) == len(times) == 128
        late = next(key for key, value in passages.items() if "Late goal" in value)
        return {
            "entries": [
                {"section": "goal", "status": "recorded", "text": "Late goal", "selectors": [late]}
            ]
        }

    synthesis.synthesize_handoff.side_effect = summarize
    markdown = access.session_handoff(document_id="claude-code:one", project="demo")["markdown"]
    assert "message=399" in markdown
    assert "Partial coverage" in markdown


@pytest.mark.parametrize(("section", "outcome"), [("files", "changed"), ("checks", "passed")])
def test_failed_command_cannot_confirm_an_edit_or_pass(handoff, section, outcome):
    from engineering_memory.normalization import Role, ToolActivity

    access, archive, _, synthesis = handoff
    item = archive.load.return_value
    first = item.conversation.messages[0]
    call = first.model_copy(
        update={
            "text": "",
            "tool_activity": (
                ToolActivity(name="Bash", request='{"id":"call-1","input":{"command":"pytest"}}'),
            ),
        }
    )
    result = first.model_copy(
        update={
            "role": Role.TOOL,
            "text": "",
            "tool_activity": (
                ToolActivity(
                    name="Bash",
                    result='{"tool_use_id":"call-1","is_error":true,"content":"Failed"}',
                ),
            ),
        }
    )
    archive.load.return_value = item.model_copy(
        update={"conversation": item.conversation.model_copy(update={"messages": (call, result)})}
    )
    synthesis.synthesize_handoff.return_value = {
        "entries": [
            {
                "section": section,
                "status": "recorded",
                "outcome": outcome,
                "text": "Completed",
                "selectors": ["1", "2"],
            }
        ]
    }
    markdown = access.session_handoff(document_id="claude-code:one", project="demo")["markdown"]
    assert "**Unknown**" in markdown
    assert "**Recorded**" not in markdown
    assert "Completed" not in markdown


def test_oversized_scope_cannot_produce_an_overlong_brief_or_broken_anchor(handoff):
    access, archive, _, _ = handoff
    with pytest.raises(AccessError, match="invalid_input"):
        access.session_handoff(document_id="claude-code:one", project="p" * 8192)
    archive.load.assert_not_called()


def test_one_large_opening_message_cannot_crowd_out_latest_evidence(handoff):
    from engineering_memory.normalization import ToolActivity

    access, archive, _, synthesis = handoff
    item = archive.load.return_value
    first = item.conversation.messages[0]
    oversized = first.model_copy(
        update={"tool_activity": (ToolActivity(name="Read", result="x" * 1024),) * 25}
    )
    last = first.model_copy(update={"text": "Latest evidence"})
    archive.load.return_value = item.model_copy(
        update={
            "conversation": item.conversation.model_copy(
                update={"messages": (oversized,) + (first,) * 255 + (last,)}
            )
        }
    )

    def summarize(passages, times):
        return {
            "entries": [
                {
                    "section": "goal",
                    "status": "recorded",
                    "text": "Latest evidence",
                    "selectors": [
                        next(key for key, value in passages.items() if "Latest evidence" in value)
                    ],
                }
            ]
        }

    synthesis.synthesize_handoff.side_effect = summarize
    markdown = access.session_handoff(document_id="claude-code:one", project="demo")["markdown"]
    assert "message=256" in markdown
    assert "Partial coverage" in markdown


@pytest.mark.parametrize(
    ("source", "name", "request_body", "result_body", "section", "outcome", "expected"),
    [
        (
            Source.CLAUDE_CODE,
            "Edit",
            '{"id":"call","input":{"file_path":"relay.conf"}}',
            (
                '{"tool_use_id":"call","is_error":false,'
                '"content":"Found no matches; no changes were made."}'
            ),
            "files",
            "changed",
            "**Unknown**",
        ),
        (
            Source.CODEX,
            "exec_command",
            '{"call_id":"call","arguments":{"cmd":"pytest"}}',
            '{"call_id":"call","output":{"exit_code":0,"stdout":"Passed."}}',
            "checks",
            "passed",
            "Command succeeded: pytest",
        ),
        (
            Source.CODEX,
            "exec_command",
            '{"call_id":"call","arguments":{"cmd":"pytest"}}',
            r'{"call_id":"call","output":"Arbitrary stdout\nExit code: 0"}',
            "checks",
            "passed",
            "**Unknown**",
        ),
    ],
)
def test_recorded_outcome_requires_actual_archive_evidence(
    handoff, source, name, request_body, result_body, section, outcome, expected
):
    from engineering_memory.normalization import Role, ToolActivity

    access, archive, _, synthesis = handoff
    item = record(source, "one", "")
    first = item.conversation.messages[0]
    call = first.model_copy(
        update={"tool_activity": (ToolActivity(name=name, request=request_body),)}
    )
    result = first.model_copy(
        update={"role": Role.TOOL, "tool_activity": (ToolActivity(name=name, result=result_body),)}
    )
    archive.load.return_value = item.model_copy(
        update={"conversation": item.conversation.model_copy(update={"messages": (call, result)})}
    )
    synthesis.synthesize_handoff.return_value = {
        "entries": [
            {
                "section": section,
                "status": "recorded",
                "outcome": outcome,
                "text": "Completed",
                "selectors": ["1", "2"],
            }
        ]
    }
    markdown = access.session_handoff(document_id=item.document_id, project="demo")["markdown"]
    assert expected in markdown
    assert ("**Recorded**" in markdown) == (expected != "**Unknown**")


def test_recorded_claim_with_only_a_tool_request_becomes_unknown(handoff):
    from engineering_memory.normalization import ToolActivity

    access, archive, _, synthesis = handoff
    item = archive.load.return_value
    call = item.conversation.messages[0].model_copy(
        update={
            "text": "",
            "tool_activity": (
                ToolActivity(name="Bash", request='{"id":"pending","input":{"command":"pytest"}}'),
            ),
        }
    )
    archive.load.return_value = item.model_copy(
        update={"conversation": item.conversation.model_copy(update={"messages": (call,)})}
    )
    synthesis.synthesize_handoff.return_value = {
        "entries": [
            {
                "section": "checks",
                "status": "recorded",
                "outcome": "passed",
                "text": "Tests passed",
                "selectors": ["1"],
            }
        ]
    }
    markdown = access.session_handoff(document_id=item.document_id, project="demo")["markdown"]
    assert "**Unknown**" in markdown
    assert "field=tool_request" in markdown
    assert "Tests passed" not in markdown
