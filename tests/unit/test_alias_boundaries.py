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

import pytest

from hermes_memory.classification.matcher import AliasMatcher
from hermes_memory.classification.rules import ProjectRule, ProjectRuleSet
from tests.synthetic import projects

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


def test_no_alias_matches_across_the_join_between_two_fields() -> None:
    """AM-7. The fields are joined with a line break, which is a boundary character.

    Asserted on the matcher rather than through a conversation, because what is being proved is
    that the join cannot be straddled — the classifier's own sweep is tested in
    `test_alias_matching.py`.
    """
    straddling = "orchard-pipe\nline-run"

    assert MATCHER.projects_named(straddling) == frozenset()
