"""The matcher as a mechanism: which projects does this text name?

Not yet the stories — those arrive in `test_alias_matching.py` (where in a conversation a name may
appear) and `test_alias_boundaries.py` (what counts as standing as a term). What is tested here is
the thing both stand on: one compiled alternation over every alias, scanned once, mapped back to
the project that declared the alias (research R4).
"""

from __future__ import annotations

import time

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


# --- cost: bounded by the text, not by the rule count (research R4) ------------------------------


def _many_projects(count: int) -> ProjectRuleSet:
    return ProjectRuleSet(
        rules=tuple(
            ProjectRule(project=f"project-{index}", aliases=(f"alias-{index}", f"a{index}-long"))
            for index in range(count)
        )
    )


def test_a_large_conversation_is_scanned_quickly() -> None:
    """A dumped manifest or a pasted log is ordinary content in this corpus."""
    text = ("some ordinary engineering prose about nothing in particular. " * 4_000) + (
        f"and finally {projects.ALIAS}"
    )
    built = AliasMatcher(projects.rule_set())

    started = time.perf_counter()
    found = built.projects_named(text)
    elapsed = time.perf_counter() - started

    assert found == frozenset({"orchard-pipeline"})
    assert elapsed < 2.0, f"scanning {len(text)} characters took {elapsed:.2f}s"


def test_a_realistic_rule_set_scans_a_realistic_conversation_quickly() -> None:
    """The honest claim, with a bound that is about the rule set a person actually writes.

    An earlier version of this test asserted that doubling the alias count does not double the
    scan, and it passed — while the scan was in fact exactly linear in the alias count, because
    `re` does not build a trie from a literal alternation. The assertion had been written loosely
    enough (`large < small * 4`) that perfectly linear growth satisfied it: a test passing for
    the wrong reason, guarding a claim the code did not honour.

    What is true, and what is worth holding, is narrower: one compiled expression and one pass
    over the text, fast enough at the scale a personal rule set reaches. A corpus-sized import at
    150 aliases spends tenths of a second per very large conversation, which is nothing beside
    the extraction it precedes (ADR-006). If a rule set ever reached thousands of aliases, this
    is where it would be felt, and indexing would become the answer research R4 declined.
    """
    text = "some ordinary engineering prose about nothing in particular. " * 2_000
    built = AliasMatcher(_many_projects(150))

    started = time.perf_counter()
    built.projects_named(text)
    elapsed = time.perf_counter() - started

    assert elapsed < 1.5, (
        f"150 aliases over {len(text)} characters took {elapsed:.2f}s. The cost is linear in "
        "both, so this is the scale at which that stops being acceptable."
    )


def test_the_scan_is_linear_in_the_alias_count_and_the_claim_says_so() -> None:
    """Measured rather than assumed, so the documentation cannot drift back.

    The bound is one-sided and generous — the point is not to pin a constant on a shared CI
    runner, but to fail if someone adds an index and forgets to correct the research, or asserts
    sublinearity again without measuring it.
    """
    text = "some ordinary engineering prose about nothing in particular. " * 1_000

    def scan(count: int) -> float:
        built = AliasMatcher(_many_projects(count))
        started = time.perf_counter()
        built.projects_named(text)
        return time.perf_counter() - started

    small = scan(100)
    large = scan(400)

    assert large > small, (
        "four times the aliases scanned no slower than a quarter of them; if the matcher now "
        "indexes rather than alternates, research R4 and plan.md say otherwise and must be fixed"
    )


def test_hundreds_of_aliases_compile_at_all() -> None:
    """A single alternation of this size is the shape research R4 chose; it must be buildable."""
    built = AliasMatcher(_many_projects(500))

    assert built.projects_named("alias-499 turned up") == frozenset({"project-499"})
