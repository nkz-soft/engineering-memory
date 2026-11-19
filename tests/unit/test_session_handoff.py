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
