"""Where the project rules live, and whether the operator said so.

The second half is the unusual part. FR-012a makes two different promises depending on one bit of
information Pydantic does not normally surface: a path the operator *chose* and that is missing is
a failure, while a path nobody chose and that is missing is a warning and an empty rule set. The
bit cannot be recovered by comparing the value to the default — an operator who sets the variable
to exactly `data/projects.toml` has still chosen it, and should get the failure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_memory.settings import PROJECT_ROOT, load_settings


def test_the_default_location_is_under_the_ignored_data_directory(
    complete_environment: dict[str, str],
) -> None:
    """`data/` is excluded by `.gitignore`, so a personal rule set cannot be committed (R7)."""
    settings = load_settings(env_file=None)

    assert settings.project_rules_path == PROJECT_ROOT / "data" / "projects.toml"


def test_a_relative_path_resolves_against_the_project_root(
    complete_environment: dict[str, str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HERMES_PROJECT_RULES_PATH", "config/projects.toml")

    from_here = load_settings(env_file=None).project_rules_path

    monkeypatch.chdir(tmp_path)
    from_elsewhere = load_settings(env_file=None).project_rules_path

    assert from_here == from_elsewhere == PROJECT_ROOT / "config" / "projects.toml"


def test_an_absolute_path_is_preserved(
    complete_environment: dict[str, str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    elsewhere = tmp_path / "mine.toml"
    monkeypatch.setenv("HERMES_PROJECT_RULES_PATH", str(elsewhere))

    assert load_settings(env_file=None).project_rules_path == elsewhere


def test_a_blank_value_is_refused(
    complete_environment: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """As for the other paths: a blank is an unfinished edit, not "use the default"."""
    monkeypatch.setenv("HERMES_PROJECT_RULES_PATH", "   ")

    with pytest.raises(Exception) as refusal:
        load_settings(env_file=None)

    assert "HERMES_PROJECT_RULES_PATH" in str(refusal.value)


def test_an_unset_path_is_reported_as_not_chosen(complete_environment: dict[str, str]) -> None:
    """The bit FR-012a turns on: nobody asked for this location."""
    settings = load_settings(env_file=None)

    assert "project_rules_path" not in settings.model_fields_set


def test_a_set_path_is_reported_as_chosen_even_when_it_equals_the_default(
    complete_environment: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HERMES_PROJECT_RULES_PATH", "data/projects.toml")

    settings = load_settings(env_file=None)

    assert settings.project_rules_path == PROJECT_ROOT / "data" / "projects.toml"
    assert "project_rules_path" in settings.model_fields_set
