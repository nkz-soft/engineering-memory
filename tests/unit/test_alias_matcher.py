"""The matcher as a mechanism: which projects does this text name?

Not yet the stories — those arrive in `test_alias_matching.py` (where in a conversation a name may
appear) and `test_alias_boundaries.py` (what counts as standing as a term). What is tested here is
the thing both stand on: one compiled alternation over every alias, scanned once, mapped back to
the project that declared the alias (research R4).
"""

from __future__ import annotations

from hermes_memory.classification.matcher import AliasMatcher
from hermes_memory.classification.rules import ProjectRule, ProjectRuleSet
from tests.synthetic import projects


def matcher(*rules: ProjectRule) -> AliasMatcher:
    return AliasMatcher(ProjectRuleSet(rules=rules or (projects.rule(),)))


def test_a_named_project_is_reported() -> None:
    found = matcher().projects_named(f"we fixed {projects.ALIAS} yesterday")

    assert found == frozenset({"orchard-pipeline"})


def test_a_text_naming_nothing_reports_nothing() -> None:
    assert matcher().projects_named("a question about nothing in particular") == frozenset()


def test_an_empty_rule_set_reports_nothing() -> None:
    assert AliasMatcher(ProjectRuleSet(rules=())).projects_named(projects.ALIAS) == frozenset()


def test_two_projects_named_are_both_reported() -> None:
    """The matcher reports; deciding between them is the classifier's job (AR-3, AR-4)."""
    found = AliasMatcher(projects.two_projects()).projects_named(
        f"migrating {projects.ALIAS} onto {projects.OTHER_ALIAS}"
    )

    assert found == frozenset({"orchard-pipeline", "lantern"})


# --- AM-1: case folding -------------------------------------------------------------------------


def test_matching_ignores_case() -> None:
    assert matcher().projects_named(f"Fixed {projects.ALIAS.upper()} today") == frozenset(
        {"orchard-pipeline"}
    )


def test_matching_folds_case_rather_than_lowercasing_it() -> None:
    """AM-1. `'Straße'.lower()` is still `'straße'`; only case folding reaches `'strasse'`.

    The rule matters for any alias a person writes in their own language, which §6's slug shape
    permits on the alias side even though the project slug itself is ASCII.
    """
    built = matcher(ProjectRule(project="strasse", aliases=("Straße",)))

    assert built.projects_named("the STRASSE service") == frozenset({"strasse"})


# --- AM-5: an alias is a literal ----------------------------------------------------------------


def test_a_dot_in_an_alias_is_a_dot() -> None:
    built = matcher(ProjectRule(project="dotted", aliases=("a.b",)))

    assert built.projects_named("axb") == frozenset()
    assert built.projects_named("a.b") == frozenset({"dotted"})


def test_regex_metacharacters_in_an_alias_are_not_metasyntax() -> None:
    """AM-5. A rule set cannot express a pattern, and cannot accidentally become one."""
    built = matcher(ProjectRule(project="bracketed", aliases=("(orchard|lantern)+",)))

    assert built.projects_named("orchard") == frozenset()
    assert built.projects_named("(orchard|lantern)+") == frozenset({"bracketed"})


# --- AM-6: the longer alias wins a position -----------------------------------------------------


def test_the_longer_alias_wins_a_position() -> None:
    """AM-6. `re` alternation is leftmost-first, so without ordering the shorter one would win."""
    built = matcher(
        ProjectRule(project="short", aliases=("nz",)),
        ProjectRule(project="long", aliases=("nz/orchard",)),
    )

    assert built.projects_named("see nz/orchard for details") == frozenset({"long"})


# --- AM-4: whitespace inside an alias -----------------------------------------------------------


def test_a_multi_word_alias_matches_across_a_line_break() -> None:
    built = matcher(ProjectRule(project="two-words", aliases=("orchard pipeline",)))

    assert built.projects_named("the orchard\npipeline run") == frozenset({"two-words"})


def test_a_multi_word_alias_matches_across_repeated_spaces() -> None:
    built = matcher(ProjectRule(project="two-words", aliases=("orchard pipeline",)))

    assert built.projects_named("the orchard   pipeline run") == frozenset({"two-words"})


def test_a_multi_word_alias_still_needs_something_between_the_words() -> None:
    built = matcher(ProjectRule(project="two-words", aliases=("orchard pipeline",)))

    assert built.projects_named("orchardpipeline") == frozenset()


# --- AM-10: occurrences are not counted ---------------------------------------------------------


def test_repeating_an_alias_changes_nothing() -> None:
    once = matcher().projects_named(projects.ALIAS)
    many = matcher().projects_named(" ".join([projects.ALIAS] * 20))

    assert once == many == frozenset({"orchard-pipeline"})


def test_the_rarer_project_is_not_outvoted() -> None:
    """AM-10. Repetition is how someone typed, not evidence of subject (research R5)."""
    found = AliasMatcher(projects.two_projects()).projects_named(
        " ".join([projects.ALIAS] * 20) + f" and once {projects.OTHER_ALIAS}"
    )

    assert found == frozenset({"orchard-pipeline", "lantern"})
