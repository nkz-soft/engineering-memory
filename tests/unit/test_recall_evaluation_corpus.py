"""The public benchmark can be imported and scoped with the production pipeline inputs."""

import hashlib
import json
from pathlib import Path

from engineering_memory.classification import AliasProjectClassifier, load_project_rules
from engineering_memory.ingestion.chatgpt import ChatGPTExportSource

CORPUS = Path(__file__).resolve().parents[2] / "evaluation" / "recall-v1"


def test_benchmark_sources_are_importable_and_scoped_to_the_recall_project() -> None:
    manifest_path = CORPUS / "benchmark.json"
    assert manifest_path.is_file(), "The recall benchmark manifest must be checked in"
    manifest = json.loads(manifest_path.read_bytes())
    export = CORPUS / "conversations.json"
    rules = CORPUS / "projects.toml"
    assert hashlib.sha256(export.read_bytes()).hexdigest() == manifest["corpus_sha256"]
    assert hashlib.sha256(rules.read_bytes()).hexdigest() == manifest["project_rules_sha256"]

    classifier = AliasProjectClassifier(load_project_rules(rules, required=True))
    documents = {
        item.conversation.document_id: item.conversation
        for item in ChatGPTExportSource(export).read()
    }
    assert len(manifest["questions"]) >= 30
    for question in manifest["questions"]:
        for topic in question["topics"]:
            for document_id in topic["document_ids"]:
                assert str(classifier.classify(documents[document_id])) == manifest["project_tag"]
