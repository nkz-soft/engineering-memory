"""Archive replay reads originals, validates identity and survives a bad record."""

import json
from unittest.mock import Mock

import pytest

from engineering_memory.archive.interface import OriginalPayload
from engineering_memory.ingestion.claude_chat.archive_source import ClaudeChatArchiveSource
from engineering_memory.ingestion.source import SourceFormatError
from engineering_memory.normalization import Source
from tests.synthetic import claude_export


def test_replay_originals_and_survive_errors():
    archive = Mock()
    archive.iter_document_ids.return_value = iter(["claude-chat:bad", "claude-chat:good"])
    archive.load_original.side_effect = [
        OriginalPayload(content=b'{"text":"PRIVATE"}', media_type="application/json"),
        OriginalPayload(
            content=json.dumps(claude_export.record("good")).encode(), media_type="application/json"
        ),
    ]
    reader = ClaudeChatArchiveSource(archive).read()
    with pytest.raises(SourceFormatError) as raised:
        next(reader)
    assert "PRIVATE" not in str(raised.value)
    assert next(reader).conversation.document_id == "claude-chat:good"
    archive.iter_document_ids.assert_called_once_with(source=Source.CLAUDE_CHAT)
    archive.load.assert_not_called()


def test_replay_refuses_wrong_identity():
    archive = Mock()
    archive.iter_document_ids.return_value = iter(["claude-chat:expected"])
    archive.load_original.return_value = OriginalPayload(
        content=json.dumps(claude_export.record("wrong")).encode(), media_type="application/json"
    )
    with pytest.raises(SourceFormatError):
        next(ClaudeChatArchiveSource(archive).read())
