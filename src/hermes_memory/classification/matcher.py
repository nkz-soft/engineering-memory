"""Which projects does this text name?

One compiled alternation over every alias of every rule, scanned once. The corpus is a decade of
history and the scan runs per conversation, so the cost that matters is the length of the text,
not the number of projects configured (specs/010-project-classifier/research.md R4).

Three details are load-bearing and none is obvious:

* **Longest alias first.** `re`'s alternation is leftmost-*first*, not leftmost-longest. Without
  the ordering, a position where both `nz` and `nz/orchard` could match would be attributed to
  whichever alias happened to be written first, which is to say to the wrong project (AM-6).
* **Case folding, not `re.IGNORECASE`.** Both the aliases and the text are folded before they
  meet. `IGNORECASE` equates `A` with `a` but not `ß` with `ss`, and an alias a person wrote in
  their own language deserves the same treatment as one they wrote in ASCII (AM-1).
* **The whole alias is escaped, then its whitespace relaxed.** Escaping makes an alias a literal,
  which is the whole of AM-5; relaxing the whitespace afterwards is what lets a multi-word alias
  survive the line break prose wraps at (AM-4).
"""

from __future__ import annotations

import re

from hermes_memory.classification.rules import ProjectRuleSet

__all__ = ["AliasMatcher"]

_WHITESPACE = re.compile(r"\s+")

_WORD_CHARACTER = r"[\w-]"
"""A letter, a digit, `_` — `\\w` under Unicode — or a hyphen.

The hyphen is the whole reason this is written out rather than using `\\b`. `\\b` is defined over
`\\w`, which treats `-` as a boundary, so the alias `orchard-pipeline` would match inside
`orchard-pipeline-ui` and every hyphenated project name would leak into every longer one. The
cost of fixing it is symmetric and intended: `orchard` alone no longer matches `orchard-pipeline`
either, and a user who wants both spellings writes both (research R2).
"""

_NOT_PRECEDED = f"(?<!{_WORD_CHARACTER})"
_NOT_FOLLOWED = f"(?!{_WORD_CHARACTER})"


def _key(text: str) -> str:
    """The form an alias and a matched span are compared in: folded, whitespace normalized."""
    return _WHITESPACE.sub(" ", text.casefold()).strip()


def _is_word_character(character: str) -> bool:
    return character.isalnum() or character in "_-"


def _as_literal(alias: str) -> str:
    """The alias as an expression: a literal, spaces relaxed, each word edge held to a boundary.

    The boundary is required only where the alias's own edge is a word character. An alias that
    ends in a boundary character of its own — `nkz-soft/` — would otherwise demand two of them in
    a row and never match anything (AM-3).
    """
    literal = r"\s+".join(re.escape(part) for part in _WHITESPACE.split(alias) if part)

    before = _NOT_PRECEDED if _is_word_character(alias[0]) else ""
    after = _NOT_FOLLOWED if _is_word_character(alias[-1]) else ""

    return f"{before}{literal}{after}"


class AliasMatcher:
    """The compiled form of a rule set. Built once, asked many times, holding no state between."""

    def __init__(self, rules: ProjectRuleSet) -> None:
        self._project_of: dict[str, str] = {
            _key(alias): rule.project for rule in rules.rules for alias in rule.aliases
        }

        # Longest first, then alphabetically, so that the compiled form of a rule set is itself
        # deterministic: two equal rule sets must compile to the same expression, or AR-6 would
        # hold by luck rather than by construction.
        ordered = sorted(self._project_of, key=lambda alias: (-len(alias), alias))

        self._expression = (
            re.compile("|".join(_as_literal(alias) for alias in ordered)) if ordered else None
        )

    def projects_named(self, text: str) -> frozenset[str]:
        """The projects this text names, each at most once however often its alias occurs.

        A set rather than a count: how often an alias was typed is an artifact of how someone
        wrote, not evidence of what they were working on (AM-10, research R5).
        """
        if self._expression is None:
            return frozenset()

        return frozenset(
            self._project_of[_key(found.group())]
            for found in self._expression.finditer(text.casefold())
        )
