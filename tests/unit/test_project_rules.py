"""The rule set refuses what it cannot classify with — RS-5 to RS-12.

Loading is the one moment in this feature where failing loudly is allowed (research R6). The
classifier has no failure path at all, so everything that can be wrong about a rule set has to be
wrong *here*, before a conversation is ever read.

Each refusal is asserted to name the offending entry. A message that merely says "invalid rule
set" would leave the user to find one bad alias in a file of fifty projects, which is how a
validation error becomes a reason to give up on configuring anything.
"""

from __future__ import annotations

import pytest

from hermes_memory.classification import ProjectRule, ProjectRulesError, ProjectRuleSet
from hermes_memory.errors import BoundaryError


def test_a_well_formed_rule_set_builds() -> None:
    built = ProjectRuleSet(
        rules=(
            ProjectRule(project="orchard-pipeline", aliases=("orchard-pipeline", "orchard")),
            ProjectRule(project="lantern", aliases=("lantern",), priority=10),
        )
    )

    assert [rule.project for rule in built.rules] == ["orchard-pipeline", "lantern"]
    assert built.rules[0].priority == 0, "an undeclared priority is 0 (AR-4's documented default)"
    assert built.rules[1].priority == 10


def test_an_empty_rule_set_is_valid() -> None:
    """RS-11. It is what FR-012a builds when no rules were configured, and it classifies nothing."""
    assert ProjectRuleSet(rules=()).rules == ()


# --- RS-6, RS-7: the project slug ---------------------------------------------------------------


@pytest.mark.parametrize("slug", ["Orchard", "orchard pipeline", "orchard:pipeline", "-orchard"])
def test_a_project_that_is_not_a_slug_is_refused(slug: str) -> None:
    """RS-6. §6's slug shape, the same one `ProjectTag` enforces."""
    with pytest.raises(ProjectRulesError) as refusal:
        ProjectRuleSet(rules=(ProjectRule(project=slug, aliases=("x",)),))

    assert slug in str(refusal.value)


def test_the_reserved_slug_is_refused() -> None:
    """RS-7. `project:unknown` is the no-match answer; a rule declaring it is indistinguishable."""
    with pytest.raises(ProjectRulesError) as refusal:
        ProjectRuleSet(rules=(ProjectRule(project="unknown", aliases=("orchard",)),))

    assert "unknown" in str(refusal.value)


def test_a_project_declared_twice_is_refused() -> None:
    """RS-8."""
    with pytest.raises(ProjectRulesError) as refusal:
        ProjectRuleSet(
            rules=(
                ProjectRule(project="orchard-pipeline", aliases=("orchard",)),
                ProjectRule(project="orchard-pipeline", aliases=("pipeline",)),
            )
        )

    assert "orchard-pipeline" in str(refusal.value)


# --- RS-9: the aliases --------------------------------------------------------------------------


@pytest.mark.parametrize("alias", ["", "   ", "---", "...", "!!"])
def test_an_alias_with_no_letter_or_digit_is_refused(alias: str) -> None:
    """RS-9. Such an alias matches everything or nothing; neither is a rule."""
    with pytest.raises(ProjectRulesError) as refusal:
        ProjectRuleSet(rules=(ProjectRule(project="orchard-pipeline", aliases=(alias,)),))

    reported = str(refusal.value)
    assert "orchard-pipeline" in reported
    assert repr(alias) in reported or alias in reported


def test_a_rule_with_no_alias_at_all_is_refused() -> None:
    """RS-9. A project nothing can name is a project nothing will ever be filed under."""
    with pytest.raises(ProjectRulesError) as refusal:
        ProjectRuleSet(rules=(ProjectRule(project="orchard-pipeline", aliases=()),))

    assert "orchard-pipeline" in str(refusal.value)


def test_one_alias_claimed_by_two_projects_is_refused() -> None:
    """RS-10. An alias that identifies two projects identifies neither."""
    with pytest.raises(ProjectRulesError) as refusal:
        ProjectRuleSet(
            rules=(
                ProjectRule(project="orchard-pipeline", aliases=("shared",)),
                ProjectRule(project="lantern", aliases=("shared",)),
            )
        )

    reported = str(refusal.value)
    assert "shared" in reported
    assert "orchard-pipeline" in reported
    assert "lantern" in reported


def test_the_duplicate_alias_check_folds_case() -> None:
    """RS-10. Matching is case-insensitive, so two spellings of one alias are one alias."""
    with pytest.raises(ProjectRulesError) as refusal:
        ProjectRuleSet(
            rules=(
                ProjectRule(project="orchard-pipeline", aliases=("Shared",)),
                ProjectRule(project="lantern", aliases=("shared",)),
            )
        )

    assert "orchard-pipeline" in str(refusal.value)


def test_one_project_may_repeat_an_alias_spelling() -> None:
    """Not RS-10: the collision rule is about two projects, and one project is one answer."""
    built = ProjectRuleSet(
        rules=(ProjectRule(project="orchard-pipeline", aliases=("Orchard", "orchard")),)
    )

    assert built.rules[0].project == "orchard-pipeline"


# --- RS-5: the shape of a rule ------------------------------------------------------------------


def test_a_priority_that_is_not_an_integer_is_refused() -> None:
    """RS-5."""
    with pytest.raises(ProjectRulesError):
        ProjectRuleSet(
            rules=(ProjectRule(project="orchard-pipeline", aliases=("x",), priority="high"),)  # type: ignore[arg-type]
        )


def test_an_unknown_key_is_refused_naming_it() -> None:
    """RS-5. A misspelled `prioirty` would otherwise be a rule that silently does less."""
    with pytest.raises(ProjectRulesError) as refusal:
        ProjectRule.model_validate(
            {"project": "orchard-pipeline", "aliases": ["x"], "prioirty": 10}
        )

    assert "prioirty" in str(refusal.value)


# --- RS-12: the error is not a boundary error ---------------------------------------------------


def test_the_error_is_not_a_boundary_error() -> None:
    """RS-12, research R6.

    #19 isolates failures per conversation by catching `BoundaryError`. A misconfigured rule set
    caught that way would be reported tens of thousands of times — once per conversation — instead
    of stopping the run once, before it started.
    """
    assert issubclass(ProjectRulesError, RuntimeError)
    assert not issubclass(ProjectRulesError, BoundaryError)


def test_a_rule_is_immutable() -> None:
    """A rule set handed to a classifier cannot be edited behind its compiled matcher."""
    built = ProjectRule(project="orchard-pipeline", aliases=("orchard",))

    with pytest.raises(ValueError):
        built.project = "lantern"  # type: ignore[misc]
