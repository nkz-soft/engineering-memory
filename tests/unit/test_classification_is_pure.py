"""`classify` cannot fail, cannot reach anything, and changes nothing — AR-7 to AR-9, PC-4.

Each of these is blocked rather than merely unobserved. A test that asserts "no file was read" by
checking that nothing appeared in a temporary directory passes for a classifier that read
`/etc/passwd`; a test that breaks `open` passes only if the call never happened.

Purity here is not tidiness. #19 runs this stage inside a per-conversation loop over a decade of
history: a classifier that touched the disk would touch it tens of thousands of times, and one
that raised would make the pipeline's failure path its ordinary path.
"""

from __future__ import annotations

import ast
import socket
from datetime import UTC, datetime
from pathlib import Path

import pytest

from engineering_memory.classification import UNKNOWN_PROJECT, alias_classifier, chain, matcher
from engineering_memory.classification.alias_classifier import AliasProjectClassifier
from engineering_memory.classification.rules import (
    ProjectRule,
    ProjectRulesError,
    ProjectRuleSet,
)
from engineering_memory.normalization import Conversation, Message, ProjectTag, Role, Source
from tests.contracts import conversations
from tests.synthetic import projects
from tests.unit.conftest import Rendered

STARTED_AT = datetime(2026, 3, 4, 9, 30, tzinfo=UTC)


def classifier() -> AliasProjectClassifier:
    return AliasProjectClassifier(projects.two_projects(first=10, second=5))


def about(text: str) -> Conversation:
    return Conversation(
        source=Source.CHATGPT,
        source_id="pure1",
        title=None,
        started_at=STARTED_AT,
        messages=(Message(role=Role.USER, text=text, sent_at=STARTED_AT),),
    )


def test_classifying_opens_no_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """AR-7. Everything that reads is spent at load time (research R6)."""
    built = classifier()

    def refuse(*args: object, **kwargs: object) -> object:
        raise AssertionError("classify opened a file")

    monkeypatch.setattr("builtins.open", refuse)
    monkeypatch.setattr("pathlib.Path.open", refuse)
    monkeypatch.setattr("pathlib.Path.read_text", refuse)

    assert built.classify(about(projects.ALIAS)) == ProjectTag(value="orchard-pipeline")


def test_classifying_opens_no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """AR-7, and §21: nothing here asks a model."""
    built = classifier()

    def refuse(*args: object, **kwargs: object) -> object:
        raise AssertionError("classify opened a socket")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)

    assert built.classify(about(projects.ALIAS)) == ProjectTag(value="orchard-pipeline")


def test_the_classifier_cannot_read_a_clock() -> None:
    """AR-7, asserted statically because patching a clock does not bite.

    `from datetime import datetime` binds the class at import time, so monkeypatching
    `datetime.datetime` afterwards leaves the module's own reference intact and the test passes
    whatever the code does. What can be asserted is that there is no reference: the modules that
    decide a project import nothing that tells the time.

    §11 keeps the import time out of a conversation's data. This keeps it out of its project.
    """
    deciding = (
        Path(alias_classifier.__file__),
        Path(matcher.__file__),
        Path(chain.__file__),
    )

    for source in deciding:
        imported = {
            node.module or ""
            for node in ast.walk(ast.parse(source.read_text(encoding="utf-8")))
            if isinstance(node, ast.ImportFrom)
        } | {
            alias.name
            for node in ast.walk(ast.parse(source.read_text(encoding="utf-8")))
            if isinstance(node, ast.Import)
            for alias in node.names
        }

        assert not imported & {"datetime", "time", "random"}, (
            f"{source.name} imports something non-deterministic; classification must answer the "
            "same way on every run (AR-6, §17)"
        )


def test_the_conversation_is_unchanged() -> None:
    """PC-4, asserted against the richest conversation the fixtures have."""
    built = classifier()

    for original in (
        conversations.conversation(),
        conversations.conversation_using_every_field(),
        about(projects.ALIAS),
    ):
        before = original.model_copy(deep=True)

        built.classify(original)

        assert original == before


def test_classifying_emits_no_log_record(rendered: Rendered) -> None:
    """AR-9, research R11.

    One record per conversation over a corpus this size is noise, #19 already reports the outcome
    per conversation, and a maintainer adding a record here would be tempted to include the
    matched alias — which is conversation content.
    """
    built = classifier()

    built.classify(about(projects.ALIAS))
    built.classify(about("nothing in particular"))

    assert rendered.text() == ""


def test_a_classifier_answers_every_conversation_the_fixtures_have() -> None:
    """AR-8. Not one of them raises, including the ones that resolve nothing."""
    built = classifier()

    for original in (
        conversations.conversation(),
        conversations.conversation_using_every_field(),
        conversations.conversation_with_a_secret(),
    ):
        assert built.classify(original) == UNKNOWN_PROJECT


HOSTILE_ALIASES = (
    "a+b",
    "[unclosed",
    "x{2,3}",
    "a" * 400,
    "0",
    "項目",
    "a\u200db",
    "C:\\Projects\thing",
)
"""Aliases a *valid* rule set can contain and a careless matcher would compile as a pattern."""

REFUSED_ALIASES = ("(((", ".*", "$^", "\\", "   ")
"""The rest are refused at load by RS-9 — they hold no letter and no digit. Asserted below, so
that "the classifier survives them" is not quietly standing in for "they never arrive"."""

HOSTILE_TEXT = (
    "",
    "\x00",
    "a" * 50_000,
    "\u202e\u202d reversed",
    "   \n\t\r   ",
    "項目 について",
    "\\" * 500,
    "a+b [unclosed x{2,3}",
)
"""Text a conversation could carry. None of it may make `classify` raise.

An unpaired surrogate is deliberately absent: #8's `Text` refuses one when the `Message` is built,
so it cannot reach a classifier, and including it here would test the model rather than this
boundary.
"""


@pytest.mark.parametrize("alias", HOSTILE_ALIASES)
def test_a_hostile_alias_classifies_without_raising(alias: str) -> None:
    """PC-5 where it is genuinely load-bearing: the regex is built from user-supplied strings.

    An alias reaches `re` through `re.escape`, so none of these is metasyntax — but that is a
    property of the implementation, and PC-5 is a property of the boundary. Asserting it over
    inputs a rule set can actually contain keeps the two from drifting apart.
    """
    built = AliasProjectClassifier(
        ProjectRuleSet(rules=(ProjectRule(project="hostile", aliases=(alias,)),))
    )

    for text in HOSTILE_TEXT:
        assert built.classify(about(text)) is not None


@pytest.mark.parametrize("alias", REFUSED_ALIASES)
def test_an_alias_of_pure_metasyntax_is_refused_at_load(alias: str) -> None:
    """RS-9, from the angle that matters here: it never becomes a pattern because it never loads."""
    with pytest.raises(ProjectRulesError):
        ProjectRuleSet(rules=(ProjectRule(project="hostile", aliases=(alias,)),))


@pytest.mark.parametrize("text", HOSTILE_TEXT, ids=lambda text: repr(text[:24]))
def test_hostile_text_classifies_without_raising(text: str) -> None:
    """AR-8. A conversation is whatever the export contained, and it still gets an answer."""
    assert classifier().classify(about(text)) is not None
