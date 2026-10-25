"""§15's three levels, composed — CH-1 to CH-5.

§15 names three levels of project detection and this feature may build only the second. What it
can leave behind is the place the others attach, and leave it demonstrated rather than described:
an extension point written as a comment is not one.

The level that will actually arrive first is not the third but the first — explicit metadata,
which Claude Code and Codex sessions carry (#27, #28) and which belongs *ahead* of the alias
rules. That is why the ordering lives in a chain rather than in a `fallback` argument on the alias
classifier: no element knows about the others, and inserting one is a composition.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hermes_memory.classification import UNKNOWN_PROJECT, ProjectClassifier
from hermes_memory.classification.alias_classifier import AliasProjectClassifier
from hermes_memory.classification.chain import ChainedProjectClassifier
from hermes_memory.normalization import Conversation, Message, ProjectTag, Role, Source
from tests.contracts.classifier import ProjectClassifierContract
from tests.synthetic import projects

STARTED_AT = datetime(2026, 3, 4, 9, 30, tzinfo=UTC)

GUESSED = ProjectTag(value="guessed-by-a-model")
ORCHARD = ProjectTag(value="orchard-pipeline")


def about(text: str) -> Conversation:
    return Conversation(
        source=Source.CHATGPT,
        source_id="chain1",
        title=None,
        started_at=STARTED_AT,
        messages=(Message(role=Role.USER, text=text, sent_at=STARTED_AT),),
    )


class Recording:
    """A stand-in for §15's level 3. It records whether it was asked, which is the whole test."""

    def __init__(self, answer: ProjectTag = GUESSED) -> None:
        self.answer = answer
        self.consulted = False

    def classify(self, conversation: Conversation) -> ProjectTag:
        self.consulted = True
        return self.answer


def alias_rules() -> AliasProjectClassifier:
    return AliasProjectClassifier(projects.rule_set())


def test_the_first_resolved_answer_wins() -> None:
    """CH-1."""
    chain = ChainedProjectClassifier((alias_rules(), Recording()))

    assert chain.classify(about(projects.ALIAS)) == ORCHARD


def test_a_later_element_is_not_consulted_once_one_resolved() -> None:
    """CH-2. The expensive level must not run for the conversations the cheap one answered."""
    fallback = Recording()
    chain = ChainedProjectClassifier((alias_rules(), fallback))

    chain.classify(about(projects.ALIAS))

    assert not fallback.consulted


def test_the_fallback_decides_what_the_rules_could_not() -> None:
    """CH-1 from the other side."""
    fallback = Recording()
    chain = ChainedProjectClassifier((alias_rules(), fallback))

    assert chain.classify(about("something else entirely")) == GUESSED
    assert fallback.consulted


def test_a_chain_resolving_nothing_is_project_unknown() -> None:
    """CH-3."""
    chain = ChainedProjectClassifier((alias_rules(), Recording(answer=UNKNOWN_PROJECT)))

    assert chain.classify(about("something else entirely")) == UNKNOWN_PROJECT


def test_an_empty_chain_is_project_unknown() -> None:
    """CH-4. A legitimate thing to build, and the cheapest possible classifier."""
    assert ChainedProjectClassifier(()).classify(about(projects.ALIAS)) == UNKNOWN_PROJECT


def test_every_element_is_consulted_in_order_until_one_answers() -> None:
    first = Recording(answer=UNKNOWN_PROJECT)
    second = Recording(answer=UNKNOWN_PROJECT)
    third = Recording()
    chain = ChainedProjectClassifier((first, second, third))

    assert chain.classify(about("nothing")) == GUESSED
    assert first.consulted and second.consulted and third.consulted


def test_a_single_element_chain_is_that_element() -> None:
    chain = ChainedProjectClassifier((alias_rules(),))

    assert chain.classify(about(projects.ALIAS)) == ORCHARD


class TestChainedProjectClassifier(ProjectClassifierContract):
    """CH-5. A chain is itself a classifier, and owes everything a classifier owes."""

    def make_classifier(self) -> ProjectClassifier:
        return ChainedProjectClassifier((alias_rules(), ChainedProjectClassifier(())))
