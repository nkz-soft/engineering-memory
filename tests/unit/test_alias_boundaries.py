"""What it means for an alias to stand as a term — AM-2, AM-3, AM-7.

Aliases are short, and short strings occur inside longer ones. The failure is silent in the
direction that matters most: over-matching does not lose a conversation, it files it under the
wrong project, where it pollutes a recall that was narrowed in order to be trusted.

This is a table of hits and misses rather than a test of an expression, because the rule is the
examples. The alphabet it implies — a word character is a letter, a digit, `_` or `-` — is a
decision with a visible consequence in both directions, and both are asserted here: it is what
makes `orchard-pipeline-ui` a miss, and equally what makes `orchard` alone a miss against the
alias `orchard-pipeline`. A user who wants both writes both (research R2).

Python's `\\b` would not do: it is defined over `\\w`, which excludes `-`, so every hyphenated
project name would leak into every longer hyphenated name that contains it.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hermes_memory.classification import UNKNOWN_PROJECT
from hermes_memory.classification.alias_classifier import AliasProjectClassifier
from hermes_memory.classification.matcher import AliasMatcher
from hermes_memory.classification.rules import ProjectRule, ProjectRuleSet
from hermes_memory.normalization import Conversation, Message, ProjectTag, Role, Source
from tests.synthetic import projects

STARTED_AT = datetime(2026, 3, 4, 9, 30, tzinfo=UTC)

MATCHER = AliasMatcher(projects.rule_set())
SHORT = AliasMatcher(ProjectRuleSet(rules=(ProjectRule(project="op", aliases=("op",)),)))


@pytest.mark.parametrize("text", projects.HITS)
def test_the_alias_standing_as_a_term_matches(text: str) -> None:
    assert MATCHER.projects_named(text) == frozenset({"orchard-pipeline"}), text


@pytest.mark.parametrize("text", projects.MISSES)
def test_the_alias_inside_a_longer_term_does_not_match(text: str) -> None:
    assert MATCHER.projects_named(text) == frozenset(), text


@pytest.mark.parametrize("text", projects.SHORT_HITS)
def test_a_short_alias_standing_as_a_term_matches(text: str) -> None:
    assert SHORT.projects_named(text) == frozenset({"op"}), text


@pytest.mark.parametrize("text", projects.SHORT_MISSES)
def test_a_short_alias_inside_a_longer_term_does_not_match(text: str) -> None:
    assert SHORT.projects_named(text) == frozenset(), text


def test_an_alias_whose_edge_is_not_a_word_character_constrains_nothing_there() -> None:
    """AM-3. Otherwise `nkz-soft/` would demand two boundaries in a row and never match."""
    matcher = AliasMatcher(
        ProjectRuleSet(rules=(ProjectRule(project="owned", aliases=("nkz-soft/",)),))
    )

    assert matcher.projects_named("nkz-soft/anything") == frozenset({"owned"})
    assert matcher.projects_named("see nkz-soft/ for the list") == frozenset({"owned"})


def test_an_alias_bounded_by_punctuation_matches() -> None:
    """AM-2. `/`, `.`, `:` and brackets are boundaries — that is what makes a path match."""
    for text in (
        f"example-org/{projects.ALIAS}.git",
        f"[{projects.ALIAS}]",
        f"{projects.ALIAS}:main",
        f"'{projects.ALIAS}'",
    ):
        assert MATCHER.projects_named(text) == frozenset({"orchard-pipeline"}), text


def test_an_underscore_is_a_word_character() -> None:
    """AM-2. `orchard_pipeline_v2` is one identifier, not an identifier containing an alias."""
    matcher = AliasMatcher(
        ProjectRuleSet(rules=(ProjectRule(project="snake", aliases=("orchard_pipeline",)),))
    )

    assert matcher.projects_named("orchard_pipeline") == frozenset({"snake"})
    assert matcher.projects_named("orchard_pipeline_v2") == frozenset()


def test_a_digit_is_a_word_character() -> None:
    matcher = AliasMatcher(
        ProjectRuleSet(rules=(ProjectRule(project="numbered", aliases=("api",)),))
    )

    assert matcher.projects_named("api2") == frozenset()
    assert matcher.projects_named("api 2") == frozenset({"numbered"})


def test_a_single_word_alias_does_not_match_across_a_line_break() -> None:
    """AM-2, and the weaker half of what AM-7 needs.

    This case is carried by the literal and boundary rules alone: `orchard-pipe` and `line-run`
    are not the alias however they are joined. It was written as the AM-7 test first, and it was
    the wrong test — it would pass with no join logic at all. The real one is below.
    """
    assert MATCHER.projects_named("orchard-pipe\nline-run") == frozenset()


def test_no_multi_word_alias_matches_across_the_join_between_two_fields() -> None:
    """AM-7, through the classifier, with the alias shape that can actually straddle a join.

    The failure this pins is a composition of two rules that are each correct: AM-4 relaxes the
    whitespace inside a multi-word alias, and the sweep concatenates fields. Join them with
    anything whitespace matches and a title ending in the alias's first word, beside a message
    beginning with its last, forges a match present in neither field. That is the direction the
    specification calls the costly one — a conversation filed under a project it never named, and
    §17 never revisits it.

    The alias shape here is the one `projects.example.toml` ships, so this is reachable from the
    configuration a user is told to copy.
    """
    classifier = AliasProjectClassifier(
        ProjectRuleSet(
            rules=(
                ProjectRule(
                    project="two-words",
                    aliases=("orchard pipeline",),
                ),
            )
        )
    )
    straddling = Conversation(
        source=Source.CHATGPT,
        source_id="straddle1",
        title="we discussed orchard",
        started_at=STARTED_AT,
        messages=(Message(role=Role.USER, text="pipeline layouts today", sent_at=STARTED_AT),),
    )

    assert classifier.classify(straddling) == UNKNOWN_PROJECT


def test_the_same_alias_wrapped_inside_one_field_still_matches() -> None:
    """The other half: fixing AM-7 must not cost AM-4, which prose wrapping depends on."""
    classifier = AliasProjectClassifier(
        ProjectRuleSet(rules=(ProjectRule(project="two-words", aliases=("orchard pipeline",)),))
    )
    wrapped = Conversation(
        source=Source.CHATGPT,
        source_id="wrapped1",
        title=None,
        started_at=STARTED_AT,
        messages=(Message(role=Role.USER, text="the orchard\npipeline run", sent_at=STARTED_AT),),
    )

    assert classifier.classify(wrapped) == ProjectTag(value="two-words")
