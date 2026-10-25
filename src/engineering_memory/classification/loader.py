"""Reading a rule set from the file a person maintains.

This is the only module in the package that touches the filesystem, and that is deliberate rather
than incidental: with every read, parse and refusal spent here, `classify` is pure by construction
instead of by discipline (specs/010-project-classifier/research.md R6).

The asymmetry `required` carries is the specification's FR-012a. A path the operator chose and
that is missing is an error; a path nobody chose and that is missing is a warning and an empty
rule set. The caller knows which it has — `Settings.model_fields_set` says so — and this module
does not import the settings, because a boundary that reached configuration would be a boundary
every consumer had to configure (Principle IV; `tests/structure/test_boundary_interfaces.py`
enforces it).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from engineering_memory.classification.rules import ProjectRulesError, ProjectRuleSet

__all__ = ["load_project_rules"]

_NO_RULES_FOUND = (
    "no project rules found; every conversation in this run will be classified "
    "project:unknown. Those tags do not correct themselves later: a re-import skips an "
    "unchanged conversation (ARCHITECTURE.md §17), so conversations retained now keep "
    "project:unknown until something reclassifies them."
)


def load_project_rules(path: Path, *, required: bool) -> ProjectRuleSet:
    """The rule set at `path`.

    `required` says whether the operator asked for this location. When they did, an absent file is
    an error naming the path. When they did not, an absent file is an empty rule set and one
    warning — the import still runs, which is what makes a first run and a dry run (#22) possible
    before anything is configured.

    Raises `ProjectRulesError`, which is **not** a `BoundaryError`: #19 isolates failures per
    conversation, and a misconfigured rule set must stop the run once rather than fail identically
    for every conversation in it.
    """
    if not path.is_file():
        if required:
            raise ProjectRulesError(
                f"no project rules at {path}, which is where they were configured to be. "
                "Create the file, or unset the setting to run without rules."
            )
        _log().warning(_NO_RULES_FOUND, path=str(path))
        return ProjectRuleSet()

    try:
        rules = ProjectRuleSet.model_validate(_read(path))
    except ProjectRulesError as refused:
        # The rule set knows what is wrong with it; only this module knows which file it came
        # from, and a reader with fifty projects needs both.
        raise ProjectRulesError(f"{path}: {refused}") from refused

    _log().info(
        "loaded project rules",
        path=str(path),
        projects=len(rules.rules),
        aliases=sum(len(rule.aliases) for rule in rules.rules),
    )
    return rules


def _read(path: Path) -> dict[str, Any]:
    """The document, with every way it can fail to be one translated to this module's error."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as unreadable:
        raise ProjectRulesError(f"{path} could not be read: {unreadable}") from unreadable
    except tomllib.TOMLDecodeError as malformed:
        raise ProjectRulesError(f"{path} is not valid TOML: {malformed}") from malformed

    try:
        return {"rules": document.get("project", ())}
    except AttributeError as not_a_table:  # pragma: no cover - tomllib always yields a dict
        raise ProjectRulesError(f"{path} is not a table of projects") from not_a_table


def _log() -> Any:
    """The logger, fetched when it is needed rather than when this module is imported.

    Not a style choice. `engineering_memory.observability` pulls OpenTelemetry, which pulls
    `socket`,
    and `tests/structure/test_boundary_interfaces.py` imports this package in a fresh interpreter
    and fails if anything forbidden arrives in `sys.modules`. Importing inside the function keeps
    the boundary's import graph clean while still emitting through the one pipeline #6 built —
    which is what guarantees these records are redacted and structured like every other
    (specs/010-project-classifier/research.md R11).
    """
    from engineering_memory.observability import get_logger

    return get_logger()
