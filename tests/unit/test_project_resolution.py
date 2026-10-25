"""What the classifier answers when the rules say nothing, one thing, or two — AR-1 to AR-6.

§15 expects a substantial share of conversations to resolve to no project. They are imported
anyway, tagged `project:unknown`, and stay retrievable — which is possible precisely because there
is one shared bank (ADR-002). So the unresolved case is the common case, and it is an answer with
a value rather than a failure or a `None`.

The ambiguous case is the one §17 cares about. A conversation that classifies one way today and
another way tomorrow is retained twice under two projects, in a store built to replicate facts
across a graph, so every assertion about ambiguity here is also an assertion about determinism.
"""

from __future__ import annotations

from datetime import UTC, datetime

from engineering_memory.classification import UNKNOWN_PROJECT, ProjectRuleSet
from engineering_memory.classification.alias_classifier import AliasProjectClassifier
from engineering_memory.normalization import Conversation, Message, ProjectTag, Role, Source
from tests.synthetic import projects

STARTED_AT = datetime(2026, 3, 4, 9, 30, tzinfo=UTC)

ORCHARD = ProjectTag(value="orchard-pipeline")
LANTERN = ProjectTag(value="lantern")


def about(text: str, *, title: str | None = None) -> Conversation:
    return Conversation(
        source=Source.CHATGPT,
        source_id="resolution1",
        title=title,
        started_at=STARTED_AT,
        messages=(Message(role=Role.USER, text=text, sent_at=STARTED_AT),),
    )


BOTH = about(f"moving {projects.ALIAS} onto {projects.OTHER_ALIAS}")


# --- AR-1: nothing matched ----------------------------------------------------------------------


def test_no_match_is_project_unknown() -> None:
    classifier = AliasProjectClassifier(projects.rule_set())

    found = classifier.classify(about("a question about nothing in particular"))

    assert found == UNKNOWN_PROJECT
    assert str(found) == "project:unknown"


def test_an_empty_rule_set_resolves_nothing_and_raises_nothing() -> None:
    """What FR-012a builds when no rules were configured."""
    classifier = AliasProjectClassifier(ProjectRuleSet(rules=()))

    assert classifier.classify(about(projects.ALIAS)) == UNKNOWN_PROJECT


def test_a_conversation_with_no_text_at_all_resolves_nothing() -> None:
    """AM-9. No title, no messages — matched against, and matching nothing."""
    empty = Conversation(
        source=Source.CHATGPT, source_id="silent1", title=None, started_at=STARTED_AT
    )

    assert AliasProjectClassifier(projects.rule_set()).classify(empty) == UNKNOWN_PROJECT


# --- AR-3, AR-4: several matched ----------------------------------------------------------------


def test_the_higher_priority_project_wins() -> None:
    """AR-3."""
    classifier = AliasProjectClassifier(projects.two_projects(first=10, second=5))

    assert classifier.classify(BOTH) == ORCHARD


def test_the_higher_priority_project_wins_whichever_side_declares_it() -> None:
    """AR-3, and a guard against an implementation that happens to prefer the first rule."""
    classifier = AliasProjectClassifier(projects.two_projects(first=5, second=10))

    assert classifier.classify(BOTH) == LANTERN


def test_a_tie_at_the_top_resolves_to_unknown() -> None:
    """AR-4. The rule set has not said which project wins, so neither does the classifier."""
    classifier = AliasProjectClassifier(projects.two_projects(first=7, second=7))

    assert classifier.classify(BOTH) == UNKNOWN_PROJECT


def test_a_rule_set_with_no_priorities_declared_ties() -> None:
    """AR-4 under the documented default: an undeclared priority is 0, so all are equal."""
    classifier = AliasProjectClassifier(projects.two_projects())

    assert classifier.classify(BOTH) == UNKNOWN_PROJECT


def test_a_tie_at_the_top_is_a_tie_whatever_lost_below_it() -> None:
    """Three matched, two tied at the top: the third losing does not break the tie."""
    classifier = AliasProjectClassifier(
        ProjectRuleSet(
            rules=(
                projects.rule("orchard-pipeline", projects.ALIAS, priority=7),
                projects.rule("lantern", projects.OTHER_ALIAS, priority=7),
                projects.rule("quarry", "quarry", priority=1),
            )
        )
    )

    found = classifier.classify(
        about(f"{projects.ALIAS}, {projects.OTHER_ALIAS} and quarry all at once")
    )

    assert found == UNKNOWN_PROJECT


def test_a_negative_priority_still_loses_rather_than_disqualifies() -> None:
    classifier = AliasProjectClassifier(projects.two_projects(first=-5, second=-10))

    assert classifier.classify(BOTH) == ORCHARD


# --- AR-6: the same answer every time -----------------------------------------------------------


def test_a_hundred_classifications_agree() -> None:
    classifier = AliasProjectClassifier(projects.two_projects(first=10, second=5))

    assert {classifier.classify(BOTH) for _ in range(100)} == {ORCHARD}


def test_the_order_rules_are_written_in_does_not_matter() -> None:
    """AR-6. Priority is declared, not positional: moving a block cannot reclassify history."""
    first = projects.rule("orchard-pipeline", projects.ALIAS, priority=10)
    second = projects.rule("lantern", projects.OTHER_ALIAS, priority=5)

    one_way = AliasProjectClassifier(ProjectRuleSet(rules=(first, second)))
    the_other = AliasProjectClassifier(ProjectRuleSet(rules=(second, first)))

    assert one_way.classify(BOTH) == the_other.classify(BOTH) == ORCHARD


def test_two_separately_built_classifiers_agree() -> None:
    """AR-6. The answer belongs to the rules, not to the process that compiled them."""
    one = AliasProjectClassifier(projects.two_projects(first=10, second=5))
    another = AliasProjectClassifier(projects.two_projects(first=10, second=5))

    assert one.classify(BOTH) == another.classify(BOTH)


def test_classifying_other_conversations_first_changes_nothing() -> None:
    """AR-6. No state accumulates between calls."""
    classifier = AliasProjectClassifier(projects.two_projects(first=10, second=5))

    for _ in range(5):
        classifier.classify(about(projects.OTHER_ALIAS))

    assert classifier.classify(BOTH) == ORCHARD
