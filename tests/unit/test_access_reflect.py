"""Reflection evidence is checked against the sanitized archive."""

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from engineering_memory.access.service import AccessError, MemoryAccess
from engineering_memory.archive import OriginalPayload
from engineering_memory.archive.local import LocalRawArchive
from tests.contracts import conversations as synth


@dataclass
class Reader:
    candidates: tuple

    def reflect(self, query, tags):
        assert query == "How did the decision evolve?"
        assert tuple(map(str, tags)) == ("project:engineering-memory",)
        return SimpleNamespace(answer="The decision changed.", evidence=self.candidates)


@pytest.mark.parametrize("scenario", ["duplicate", "missing", "wrong_project", "mismatched"])
def test_reflection_returns_only_archive_validated_references(tmp_path, scenario):
    archive = LocalRawArchive(tmp_path / "archive")
    enriched = synth.enrich(synth.conversation_using_every_field())
    if scenario != "missing":
        archive.store(
            enriched, OriginalPayload(content=b"private original", media_type="text/plain")
        )
    provenance = enriched.provenance
    if scenario == "wrong_project":
        candidate = provenance.model_copy(update={"project": "other"})
        candidates = (provenance, candidate)
    elif scenario == "mismatched":
        candidate = provenance.model_copy(update={"importer_version": "stale"})
        candidates = (candidate,)
    else:
        candidates = (provenance, provenance)
    access = MemoryAccess(None, archive, reflection=Reader(candidates))

    result = access.reflect(query="How did the decision evolve?", project="engineering-memory")

    if scenario == "duplicate":
        assert result["status"] == "completed"
        assert result["answer"] == "The decision changed."
        assert [ref["document_id"] for ref in result["references"]] == [enriched.document_id]
        assert access.get_conversation(document_id=enriched.document_id)["messages"]
    else:
        assert result == {"status": "insufficient_evidence", "references": []}


@pytest.mark.parametrize("query, project", [(" ", "project-a"), ("question", "a:b")])
def test_reflection_rejects_invalid_input(query, project):
    with pytest.raises(AccessError, match="invalid_input"):
        MemoryAccess(None, None).reflect(query=query, project=project)
