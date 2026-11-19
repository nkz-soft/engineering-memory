"""Access verifies current normalized evidence and scoped viewer pages."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engineering_memory.access.service import AccessError, MemoryAccess
from engineering_memory.normalization import Source
from tests.unit.test_deep_recall import record


def test_evidence_is_read_from_current_normalized_record():
    archive, index, memory = Mock(), Mock(), Mock()
    item = record(Source.CODEX, "one", "PR https://github.com/demo/repo/pull/1")
    archive.load.return_value = item
    from engineering_memory.access.neighborhood_evidence import Node, snapshot_of

    index.evidence.return_value = SimpleNamespace(
        project="demo",
        origin=Node("session", "codex:one", "One"),
        target=Node("pr", "https://github.com/demo/repo/pull/1", "PR 1"),
        relation="pr_reference",
        document_id="codex:one",
        message=0,
        tool=None,
        field="text",
        snapshot=snapshot_of(item),
    )
    access = MemoryAccess(memory, archive, neighborhood_index=index)

    result = access.neighborhood_evidence(project="demo", handle="1" * 32)

    assert result["relation"] == "pr_reference"
    assert result["text"] == item.conversation.messages[0].text
    assert result["selector"] == {
        "document_id": "codex:one",
        "message": 0,
        "tool": None,
        "field": "text",
        "snapshot": snapshot_of(item),
    }
    archive.load.assert_called_once_with("codex:one")
    archive.load_original.assert_not_called()
    assert not memory.mock_calls


@pytest.mark.parametrize("changed", ["text", "project", "document"])
def test_guarded_viewer_rejects_replaced_or_mis_scoped_snapshot(changed):
    archive = Mock()
    original = record(Source.CODEX, "one", "Original")
    replacement = {
        "text": record(Source.CODEX, "one", "Replacement"),
        "project": record(Source.CODEX, "one", "Original", project="other"),
        "document": record(Source.CODEX, "two", "Original"),
    }[changed]
    archive.load.side_effect = [original, replacement]
    access = MemoryAccess(Mock(), archive)
    from engineering_memory.access.neighborhood_evidence import snapshot_of

    request = {"document_id": "codex:one", "project": "demo", "snapshot": snapshot_of(original)}
    assert access.get_neighborhood_conversation(**request)["messages"][0]["text"] == "Original"
    with pytest.raises(AccessError, match=r"^not_found$"):
        access.get_neighborhood_conversation(**request)
    assert archive.load.call_count == 2


@pytest.mark.parametrize(
    ("relation", "identity", "literal"),
    [
        (
            "pr_reference",
            "https://github.com/demo/repo/pull/1",
            "https://GitHub.com/demo/repo/pull/1",
        ),
        ("file_edit", "src/app.py", r"D:\\workspace\\src\\app.py"),
    ],
)
def test_evidence_preview_contains_recorded_target(relation, identity, literal):
    from engineering_memory.access.neighborhood_evidence import Node, snapshot_of

    text = "Unrelated preamble. " * 300 + literal
    archive, index = Mock(), Mock()
    item = record(Source.CODEX, "one", text)
    archive.load.return_value = item
    index.evidence.return_value = SimpleNamespace(
        project="demo",
        origin=Node("session", "codex:one", "One"),
        target=Node("pr" if relation == "pr_reference" else "file", identity, identity),
        relation=relation,
        document_id="codex:one",
        message=0,
        tool=None,
        field="text",
        snapshot=snapshot_of(item),
    )
    result = MemoryAccess(Mock(), archive, neighborhood_index=index).neighborhood_evidence(
        project="demo",
        handle="a" * 32,
    )
    assert literal in result["text"]
    assert len(result["text"]) <= 2_000
