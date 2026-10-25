"""The rules a classifier answers from, and everything that can be wrong with them.

ARCHITECTURE.md §15 level 2 is "match known repository names, paths, project names and aliases".
This module is the vocabulary that sentence implies, and the place every refusal lives.

It is deliberately the *only* place in this package that refuses anything. `classify` has no
failure path — PC-5 and contracts/errors.md E8 make an unresolved project an ordinary answer, so a
classifier that raised would make the pipeline's failure path its common path. The two obligations
coexist by being about different moments: a rule set is validated when it is built, and a built
rule set cannot be wrong afterwards (specs/010-project-classifier/research.md R6).

Hence `ProjectRulesError` is a plain `RuntimeError` and **not** a `BoundaryError`. #19 isolates
failures per conversation by catching `BoundaryError`; a misconfigured rule set caught that way
would be reported once per conversation across the whole corpus instead of stopping the run before
it started.
"""

from __future__ import annotations

import re
from typing import Any, Self

from pydantic import ValidationError, model_validator

from engineering_memory.classification.classifier import UNKNOWN_PROJECT
from engineering_memory.normalization.base import FrozenModel, Slug

__all__ = ["ProjectRule", "ProjectRuleSet", "ProjectRulesError", "alias_key"]

_WHITESPACE = re.compile(r"\s+")


def alias_key(alias: str) -> str:
    """The identity of an alias: case-folded, whitespace runs collapsed, ends trimmed.

    One function because two places need the same answer and disagreeing was a defect rather
    than a possibility. `ProjectRuleSet` uses it to refuse an alias claimed by two projects
    (RS-10), and the matcher uses it to map a matched span back to its project. When the two
    normalizations differed by so much as a stripped space, a pair like `foo bar` and
    `foo  bar` passed validation and then collided in the matcher, where the last declaration
    won and the other project's alias silently stopped existing — the exact outcome RS-10 says
    is unacceptable.

    Case folding rather than lowercasing, for the reason the matcher gives: `ß` and `ss` are
    one alias to a reader, and only folding agrees.
    """
    return _WHITESPACE.sub(" ", alias.casefold()).strip()


class ProjectRulesError(RuntimeError):
    """A rule set that cannot be used. Raised at load time, never at classify time (RS-12)."""


def _describe(invalid: ValidationError) -> str:
    """Render a validation failure so it names the entry rather than the shape.

    The input value is included, which the settings loader of #5 deliberately withholds — and the
    difference is the point. There, a value may be a credential. Here it is a project name, an
    alias or a priority, which is exactly what the reader has to find in their file.
    """
    return "; ".join(
        f"{'.'.join(str(part) for part in entry['loc']) or 'rule set'}: {entry['msg']}"
        f" (got {entry['input']!r})"
        for entry in invalid.errors()
    )


class _RefusesLoudly(FrozenModel):
    """Translates Pydantic's failure into this module's, so callers catch one kind of error.

    Three entry points rather than two, and the third is the one worth naming: the loader
    validates whole documents with `model_validate`, tests and composition code construct rules
    directly, and nothing yet calls `model_validate_json` — which is exactly why it is covered. An
    uncovered constructor is a `ValidationError` escaping as soon as someone reaches for the
    obvious method, in a module whose whole claim is that it raises one kind of error.
    """

    def __init__(self, **data: Any) -> None:
        try:
            super().__init__(**data)
        except ValidationError as invalid:
            raise ProjectRulesError(_describe(invalid)) from invalid

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any) -> Self:
        try:
            return super().model_validate(obj, **kwargs)
        except ValidationError as invalid:
            raise ProjectRulesError(_describe(invalid)) from invalid

    @classmethod
    def model_validate_json(cls, json_data: Any, **kwargs: Any) -> Self:
        try:
            return super().model_validate_json(json_data, **kwargs)
        except ValidationError as invalid:
            raise ProjectRulesError(_describe(invalid)) from invalid


class ProjectRule(_RefusesLoudly):
    """One project: what it is called, what names it, and how it wins an argument.

    `priority` is a declared field rather than the rule's position in the file. Position would mean
    that moving a block in the configuration reclassifies history, and §17 requires a re-import to
    land where the first import did (research R5).
    """

    project: Slug
    aliases: tuple[str, ...]
    priority: int = 0

    @model_validator(mode="after")
    def _the_rule_can_identify_something(self) -> ProjectRule:
        if self.project == UNKNOWN_PROJECT.value:
            raise ValueError(
                f"the project slug {self.project!r} is reserved: §15 uses it for a conversation no "
                "rule matched, so a rule declaring it could not be told from the absence of a rule"
            )

        if not self.aliases:
            raise ValueError(
                f"project {self.project!r} declares no alias, so nothing could ever be filed "
                "under it"
            )

        for alias in self.aliases:
            if not any(character.isalnum() for character in alias):
                raise ValueError(
                    f"project {self.project!r} declares the alias {alias!r}, which holds no letter "
                    "and no digit; such an alias matches everything or nothing"
                )

        return self


class ProjectRuleSet(_RefusesLoudly):
    """The validated collection a classifier is built from.

    An **empty** rule set is valid, and is what FR-012a builds when no rules were configured: it
    classifies every conversation as `project:unknown`, which §15 already treats as an ordinary
    answer.
    """

    rules: tuple[ProjectRule, ...] = ()

    @model_validator(mode="after")
    def _every_project_and_every_alias_is_unique(self) -> ProjectRuleSet:
        seen_projects: set[str] = set()
        claimed_by: dict[str, str] = {}

        for rule in self.rules:
            if rule.project in seen_projects:
                raise ValueError(
                    f"project {rule.project!r} is declared twice; merge the two entries, because "
                    "two rules for one project cannot disagree usefully"
                )
            seen_projects.add(rule.project)

            for alias in rule.aliases:
                folded = alias_key(alias)
                owner = claimed_by.get(folded)
                if owner is not None and owner != rule.project:
                    raise ValueError(
                        f"the alias {alias!r} is declared by both {owner!r} and "
                        f"{rule.project!r}; an alias that identifies two projects identifies "
                        "neither"
                    )
                claimed_by[folded] = rule.project

        return self
