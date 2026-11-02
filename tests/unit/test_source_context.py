"""Source context must survive archives, be sanitized, and leave legacy hashes alone."""

import pytest

from engineering_memory.classification import (
    AliasProjectClassifier,
    ChainedProjectClassifier,
    ProjectRule,
    ProjectRuleSet,
)
from engineering_memory.normalization import Conversation
from engineering_memory.sanitization import PatternSecretSanitizer
from tests.contracts.conversations import conversation


def test_context_roundtrip_and_legacy_hash():
    old = conversation()
    enriched = old.model_copy(
        update={
            "repository": "https://example.test/org/orchard.git",
            "working_directory": "/work/orchard",
        }
    )
    assert Conversation.model_validate_json(enriched.model_dump_json()) == enriched
    assert enriched.content_hash() == old.content_hash()
    assert Conversation.model_validate(old.model_dump()).repository is None


def test_context_secret_is_scanned_without_changing_identity():
    value = conversation().model_copy(
        update={
            "repository": "password=" + "synthetic-secret-123",
            "working_directory": "/work/password=" + "synthetic-secret-123",
        }
    )
    clean, report = PatternSecretSanitizer().sanitize(value)
    assert "synthetic-secret-123" not in clean.model_dump_json()
    assert report.counts
    assert clean.document_id == value.document_id


@pytest.mark.parametrize(
    "repository,cwd,want",
    [
        ("https://example.test/org/Orchard.git", "/work/other", "orchard"),
        ("git@example.test:org/Orchard.git", None, "orchard"),
        (None, "C:\\work\\Orchard\\", "orchard"),
        (None, "/work/Orchard/", "orchard"),
        ("/work/???", "/work/real", "real"),
        (None, "/", "unknown"),
        (None, None, "unknown"),
    ],
)
def test_metadata_project_before_prose(repository, cwd, want):
    from engineering_memory.classification.metadata_classifier import MetadataProjectClassifier

    rules = ProjectRuleSet(rules=())
    value = conversation().model_copy(update={"repository": repository, "working_directory": cwd})
    assert MetadataProjectClassifier(rules).classify(value).value == want


def test_metadata_alias_mapping_and_chain_precedence():
    from engineering_memory.classification.metadata_classifier import MetadataProjectClassifier

    rules = ProjectRuleSet(
        rules=(
            ProjectRule(project="real-project", aliases=("orchard",)),
            ProjectRule(project="prose-project", aliases=("Wolverine",)),
        )
    )
    chain = ChainedProjectClassifier(
        (MetadataProjectClassifier(rules), AliasProjectClassifier(rules))
    )
    assert (
        chain.classify(
            conversation().model_copy(update={"working_directory": "/work/orchard"})
        ).value
        == "real-project"
    )
    assert chain.classify(conversation()).value == "prose-project"
