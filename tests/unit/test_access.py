"""Consumer retrieval contracts use synthetic history and injected boundaries."""

import json
from unittest.mock import Mock

import pytest

from engineering_memory.access.service import AccessError, MemoryAccess
from engineering_memory.archive import ArchiveDocumentNotFound, ArchiveRejected, ArchiveUnavailable
from engineering_memory.memory.interface import MemoryStoreRejected, MemoryStoreUnavailable
from tests.contracts import conversations as synth
from tests.fakes.store import InMemoryMemoryStore


@pytest.fixture
def access():
    enriched = synth.enrich(synth.conversation_using_every_field())
    memory = InMemoryMemoryStore()
    memory.retain(enriched)
    archive = Mock()
    archive.load.return_value = enriched
    return MemoryAccess(memory, archive), archive, enriched


def test_search_provenance_and_original_time(access):
    service, archive, enriched = access
    result = service.search_memory(query="failing log")
    match = result["results"][0]
    assert match["document_id"] == enriched.document_id
    assert match["provenance"] == enriched.provenance.model_dump(mode="json")
    assert match["started_at"] == enriched.conversation.model_dump(mode="json")["started_at"]
    archive.load_original.assert_not_called()


def test_search_empty_and_conjunctive_filters(access):
    service, _, enriched = access
    assert service.search_memory(query="missing")["results"] == []
    assert service.search_memory(query="failing log", tags=["project:another"])["results"] == []
    tags = [str(tag) for tag in enriched.tags]
    assert len(service.search_memory(query="failing log", tags=tags)["results"]) == 1


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": " "},
        {"query": 7},
        {"query": "x", "limit": True},
        {"query": "x", "limit": 0},
        {"query": "x", "limit": 101},
        {"query": "x", "tags": ["invalid:value"]},
        {"query": "x", "tags": ["project:Bad Value"]},
        {"query": "x", "tags": "source:chatgpt"},
    ],
)
def test_search_invalid_before_boundary(access, arguments):
    service, archive, _ = access
    with pytest.raises(AccessError, match="invalid_input"):
        service.search_memory(**arguments)
    archive.load.assert_not_called()


@pytest.mark.parametrize(
    "error, code",
    [
        (ArchiveDocumentNotFound("PRIVATE"), "not_found"),
        (ArchiveRejected("PRIVATE"), "corrupt_record"),
        (ArchiveUnavailable("PRIVATE"), "unavailable"),
        (RuntimeError("PRIVATE"), "internal"),
    ],
)
def test_archive_safe_errors(access, error, code):
    service, archive, enriched = access
    archive.load.side_effect = error
    with pytest.raises(AccessError, match=code) as raised:
        service.get_conversation(document_id=enriched.document_id)
    assert "PRIVATE" not in str(raised.value)
    assert raised.value.__context__ is None


@pytest.mark.parametrize(
    "error, code",
    [
        (MemoryStoreUnavailable("PRIVATE"), "unavailable"),
        (MemoryStoreRejected("PRIVATE"), "rejected"),
    ],
)
def test_memory_safe_errors(access, error, code):
    _, archive, _ = access
    memory = Mock()
    memory.recall.side_effect = error
    with pytest.raises(AccessError, match=code):
        MemoryAccess(memory, archive).search_memory(query="x")


def test_paging_reconstructs_normalized_messages(access):
    service, archive, enriched = access
    messages, offset = [], 0
    while True:
        page = service.get_conversation(
            document_id=enriched.document_id, offset=offset, page_size=1
        )
        messages.extend(page["messages"])
        offset = page["next_offset"]
        if offset is None:
            break
    assert messages == enriched.conversation.model_dump(mode="json")["messages"]
    assert "original" not in json.dumps(page)
    archive.load_original.assert_not_called()
    end = service.get_conversation(document_id=enriched.document_id, offset=1000)
    assert end["messages"] == [] and end["next_offset"] is None


@pytest.mark.parametrize(
    "arguments",
    [
        {"document_id": "../private"},
        {"document_id": "chatgpt:../private"},
        {"document_id": "unknown:abc"},
        {"document_id": "chatgpt:"},
        {"document_id": "chatgpt:a", "offset": -1},
        {"document_id": "chatgpt:a", "offset": True},
        {"document_id": "chatgpt:a", "page_size": 101},
        {"document_id": "chatgpt:a", "page_size": 0},
    ],
)
def test_page_invalid_before_archive(access, arguments):
    service, archive, _ = access
    with pytest.raises(AccessError, match="invalid_input"):
        service.get_conversation(**arguments)
    archive.load.assert_not_called()


def test_competing_projects_and_result_limit():
    memory, archive = InMemoryMemoryStore(), Mock()
    records = [
        synth.enrich(
            synth.conversation("intended", text="Cobalt relay is selected."), project="orchard"
        ),
        synth.enrich(
            synth.conversation("distractor", text="Cobalt relay was rejected."), project="another"
        ),
    ]
    for item in records:
        memory.retain(item)
    archive.load.side_effect = {item.document_id: item for item in records}.__getitem__
    service = MemoryAccess(memory, archive)
    assert len(service.search_memory(query="Cobalt relay")["results"]) == 2
    assert len(service.search_memory(query="Cobalt relay", limit=1)["results"]) == 1
    scoped = service.search_memory(query="Cobalt relay", tags=["project:orchard", "source:chatgpt"])
    assert [item["document_id"] for item in scoped["results"]] == ["chatgpt:intended"]
