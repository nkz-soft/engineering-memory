"""Validate the versioned benchmark and score each expected topic once."""

import json
import re
import unicodedata
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from engineering_memory.ingestion.chatgpt.conversation import parse_record
from engineering_memory.ingestion.chatgpt.thread import UnreadableRecord

Category = Literal[
    "architecture-decisions",
    "technology-choices",
    "debugging-investigations",
    "root-causes",
    "failed-approaches",
    "infrastructure",
    "operational-lessons",
]
CATEGORIES: tuple[Category, ...] = (
    "architecture-decisions",
    "technology-choices",
    "debugging-investigations",
    "root-causes",
    "failed-approaches",
    "infrastructure",
    "operational-lessons",
)
MIN_QUESTIONS = 30
RECALL_LIMIT = 10
PROJECT_TAG = "project:recall-benchmark"
VersionOne = Annotated[int, Field(ge=1, le=1)]
Limit = Annotated[int, Field(ge=RECALL_LIMIT, le=RECALL_LIMIT)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Identifier = Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
Nonblank = Annotated[str, Field(pattern=r"\S")]
_WORD = re.compile(r"[^\W_]+")


class EvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


def tokens(text: str) -> tuple[str, ...]:
    return tuple(_WORD.findall(unicodedata.normalize("NFKC", text).casefold()))


def _contains(phrase: tuple[str, ...], words: tuple[str, ...]) -> bool:
    return any(words[i : i + len(phrase)] == phrase for i in range(len(words) - len(phrase) + 1))


def _require_unique(values: Sequence, subject: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {subject}")


class Topic(EvaluationModel):
    id: Identifier
    aliases: Annotated[list[Nonblank], Field(min_length=1)]
    document_ids: Annotated[list[Nonblank], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_aliases(self) -> Self:
        phrases = [tokens(alias) for alias in self.aliases]
        if not all(phrases):
            raise ValueError("topic alias needs a word")
        _require_unique(phrases, "topic alias")
        _require_unique(self.document_ids, "supporting document")
        return self


class Question(EvaluationModel):
    id: Identifier
    category: Category
    query: Nonblank
    topics: Annotated[list[Topic], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_topics(self) -> Self:
        _require_unique([topic.id for topic in self.topics], "topic ID")
        return self


class Benchmark(EvaluationModel):
    schema_version: VersionOne
    project_tag: Literal["project:recall-benchmark"]
    limit: Limit
    corpus_sha256: Digest
    project_rules_sha256: Digest
    questions: Annotated[list[Question], Field(min_length=MIN_QUESTIONS)]
    _manifest_sha256: str = PrivateAttr()

    @property
    def manifest_sha256(self) -> str:
        return self._manifest_sha256

    @model_validator(mode="after")
    def validate_questions(self) -> Self:
        _require_unique([question.id for question in self.questions], "question ID")
        _require_unique([tokens(question.query) for question in self.questions], "query")
        if {question.category for question in self.questions} != set(CATEGORIES):
            raise ValueError("benchmark must cover all categories")
        return self


def _source_texts(corpus: bytes) -> dict[str, list[tuple[str, ...]]]:
    records = json.loads(corpus)
    if not isinstance(records, list) or not records:
        raise ValueError("corpus must contain conversations")
    texts = {}
    for record in records:
        try:
            conversation = parse_record(record).conversation
        except (UnreadableRecord, TypeError, ValueError):
            raise ValueError("invalid corpus conversation") from None
        if conversation.document_id in texts:
            raise ValueError("duplicate corpus document ID")
        texts[conversation.document_id] = [
            tokens(message.text) for message in conversation.messages
        ]
    return texts


def load_benchmark(path: Path) -> Benchmark:
    manifest = path.read_bytes()
    benchmark = Benchmark.model_validate_json(manifest)
    corpus = path.with_name("conversations.json").read_bytes()
    rules = path.with_name("projects.toml").read_bytes()
    if sha256(corpus).hexdigest() != benchmark.corpus_sha256:
        raise ValueError("corpus digest mismatch")
    if sha256(rules).hexdigest() != benchmark.project_rules_sha256:
        raise ValueError("project rules digest mismatch")
    texts = _source_texts(corpus)
    for question in benchmark.questions:
        for topic in question.topics:
            if not all(document_id in texts for document_id in topic.document_ids):
                raise ValueError("topic references an unknown corpus document")
            if not any(
                _contains(tokens(alias), message)
                for alias in topic.aliases
                for document_id in topic.document_ids
                for message in texts[document_id]
            ):
                raise ValueError("topic has no supporting phrase in the corpus")
    benchmark._manifest_sha256 = sha256(manifest).hexdigest()
    return benchmark


class RecallMatch(EvaluationModel):
    # Ignore the MCP response's other provenance and ranking fields.
    model_config = ConfigDict(extra="ignore")
    document_id: Nonblank
    content: str


class QuestionOutcome(EvaluationModel):
    id: Identifier
    category: Category
    expected_topic_ids: Annotated[list[Identifier], Field(min_length=1)]
    matched_topic_ids: list[Identifier]

    @model_validator(mode="after")
    def validate_topic_ids(self) -> Self:
        _require_unique(self.expected_topic_ids, "expected topic ID")
        _require_unique(self.matched_topic_ids, "matched topic ID")
        if not set(self.matched_topic_ids).issubset(self.expected_topic_ids):
            raise ValueError("matched topic must be expected")
        return self

    @property
    def score(self) -> float:
        return len(self.matched_topic_ids) / len(self.expected_topic_ids)


def score_question(question: Question, matches: Sequence[RecallMatch]) -> QuestionOutcome:
    evidence = [(match.document_id, tokens(match.content)) for match in matches[:RECALL_LIMIT]]
    matched = [
        topic.id
        for topic in question.topics
        if any(
            _contains(tokens(alias), words)
            for document_id, words in evidence
            if document_id in topic.document_ids
            for alias in topic.aliases
        )
    ]
    return QuestionOutcome(
        id=question.id,
        category=question.category,
        expected_topic_ids=[topic.id for topic in question.topics],
        matched_topic_ids=matched,
    )
