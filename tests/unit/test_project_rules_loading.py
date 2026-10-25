"""Reading a rule set from a file — RS-1 to RS-5, RS-11, RS-13.

The asymmetry in the middle of this suite is the answer to the specification's second question,
and the reason it is worth reading twice: a path the operator **chose** and that is missing is an
error, while a path nobody chose and that is missing is a warning and an empty rule set. "Did not
configure" and "configured wrongly" are different mistakes, and only one of them should stop a
first run.

The warning says more than "no rules found", and the extra sentence is the point: §17 skips an
unchanged conversation on re-import, so tags written by a rule-less run do not correct themselves
when the rules arrive. Nobody reads that out of the documentation in time; they read it out of the
run that is about to do it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from engineering_memory.classification import ProjectRulesError, load_project_rules
from tests.synthetic import projects
from tests.unit.conftest import Rendered

VALID = projects.document(
    projects.entry("orchard-pipeline", "orchard-pipeline", "orchard", priority=10),
    projects.entry("lantern", "lantern"),
)


def write(directory: Path, contents: str, name: str = "projects.toml") -> Path:
    path = directory / name
    path.write_text(contents, encoding="utf-8")
    return path


# --- RS-1: a rule set loads ---------------------------------------------------------------------


def test_a_valid_document_loads(tmp_path: Path, rendered: Rendered) -> None:
    loaded = load_project_rules(write(tmp_path, VALID), required=True)

    assert [rule.project for rule in loaded.rules] == ["orchard-pipeline", "lantern"]
    assert loaded.rules[0].aliases == ("orchard-pipeline", "orchard")
    assert loaded.rules[0].priority == 10
    assert loaded.rules[1].priority == 0, "an omitted priority is the documented default"


def test_the_shipped_example_parses_and_validates(rendered: Rendered) -> None:
    """`projects.example.toml` is documentation that can rot; this is what stops it."""
    example = Path(__file__).resolve().parents[2] / "projects.example.toml"

    loaded = load_project_rules(example, required=True)

    assert loaded.rules, "the example should show at least one project"


# --- RS-2, RS-3: present, absent, asked for, not asked for --------------------------------------


def test_a_path_that_was_asked_for_and_is_missing_is_an_error(tmp_path: Path) -> None:
    """RS-2."""
    missing = tmp_path / "nowhere.toml"

    with pytest.raises(ProjectRulesError) as refusal:
        load_project_rules(missing, required=True)

    assert str(missing) in str(refusal.value)


def test_a_default_path_that_is_missing_is_a_warning(tmp_path: Path, rendered: Rendered) -> None:
    """RS-3, FR-012a. The run proceeds, and says what that means."""
    missing = tmp_path / "projects.toml"

    loaded = load_project_rules(missing, required=False)

    assert loaded.rules == ()

    record = rendered.one()
    assert record["level"] == "warning"
    assert record["path"] == str(missing), (
        "the path goes in a field of its own rather than into the sentence: it is what the "
        "reader has to act on, and on Windows it is full of backslashes a message would escape"
    )


def test_the_warning_says_what_this_run_will_do(tmp_path: Path, rendered: Rendered) -> None:
    """FR-012a."""
    load_project_rules(tmp_path / "projects.toml", required=False)

    assert "project:unknown" in str(rendered.one())


def test_the_warning_says_that_a_re_import_will_not_revisit_those_conversations(
    tmp_path: Path, rendered: Rendered
) -> None:
    """FR-012b. The consequence that is neither obvious nor reversible by re-running."""
    load_project_rules(tmp_path / "projects.toml", required=False)

    reported = str(rendered.one()).lower()
    assert "re-import" in reported or "reimport" in reported
    assert "unchanged" in reported or "not revisit" in reported


def test_a_present_file_is_loaded_whether_or_not_it_was_asked_for(
    tmp_path: Path, rendered: Rendered
) -> None:
    """The asymmetry is only about absence."""
    path = write(tmp_path, VALID)

    assert load_project_rules(path, required=False) == load_project_rules(path, required=True)


# --- RS-4, RS-5: the file is there and wrong ----------------------------------------------------


def test_a_file_that_is_not_toml_is_an_error(tmp_path: Path) -> None:
    """RS-4."""
    path = write(tmp_path, "this is not: [toml\n")

    with pytest.raises(ProjectRulesError) as refusal:
        load_project_rules(path, required=True)

    assert str(path) in str(refusal.value)


def test_a_document_with_a_rule_missing_its_project_is_an_error(tmp_path: Path) -> None:
    """RS-5."""
    path = write(tmp_path, '[[project]]\naliases = ["orchard"]\n')

    with pytest.raises(ProjectRulesError) as refusal:
        load_project_rules(path, required=True)

    assert "project" in str(refusal.value)


def test_a_document_with_an_unknown_key_is_an_error_naming_it(tmp_path: Path) -> None:
    """RS-5. `prioirty` would otherwise be a rule that silently does less than its author meant."""
    path = write(
        tmp_path, '[[project]]\nproject = "orchard"\naliases = ["orchard"]\nprioirty = 10\n'
    )

    with pytest.raises(ProjectRulesError) as refusal:
        load_project_rules(path, required=True)

    assert "prioirty" in str(refusal.value)


def test_a_document_whose_top_level_is_wrong_is_an_error(tmp_path: Path) -> None:
    """A `[project]` table instead of `[[project]]` is the likeliest TOML slip there is."""
    path = write(tmp_path, '[project]\nproject = "orchard"\naliases = ["orchard"]\n')

    with pytest.raises(ProjectRulesError) as refusal:
        load_project_rules(path, required=True)

    assert "project" in str(refusal.value)


def test_a_rule_set_refused_by_validation_is_an_error_naming_the_file(tmp_path: Path) -> None:
    """RS-5 and RS-10 together: the refusal comes from the rule set, the path comes from here."""
    path = write(
        tmp_path,
        projects.document(
            projects.entry("orchard-pipeline", "shared"),
            projects.entry("lantern", "shared"),
        ),
    )

    with pytest.raises(ProjectRulesError) as refusal:
        load_project_rules(path, required=True)

    reported = str(refusal.value)
    assert str(path) in reported
    assert "shared" in reported


# --- RS-11: an empty file is a choice -----------------------------------------------------------


def test_a_file_holding_no_project_loads_as_an_empty_rule_set(
    tmp_path: Path, rendered: Rendered
) -> None:
    """RS-11. Writing an empty file is a choice, unlike not writing one — so no warning."""
    loaded = load_project_rules(write(tmp_path, "# nothing yet\n"), required=False)

    assert loaded.rules == ()
    assert not [record for record in rendered.records() if record["level"] == "warning"]


# --- RS-13: what loading says ------------------------------------------------------------------


def test_loading_reports_what_it_loaded(tmp_path: Path, rendered: Rendered) -> None:
    """RS-13. One record, naming the path and the two counts."""
    path = write(tmp_path, VALID)

    load_project_rules(path, required=True)

    record = rendered.one()
    assert record["level"] == "info"
    assert record["projects"] == 2
    assert record["aliases"] == 3
    assert record["path"] == str(path)


def test_no_record_carries_a_conversation(tmp_path: Path, rendered: Rendered) -> None:
    """Loading happens before any conversation is read, and the records show it."""
    load_project_rules(write(tmp_path, VALID), required=True)

    assert "conversation" not in str(rendered.one()).lower()
