"""Synthesized project rules, and the near-miss pairs the boundary rule is pinned by.

Never a real rule set: a real one is a list of someone's repositories, local paths and the
shorthand they type, and this repository is public (CLAUDE.md, research R12). Every name below is
invented.

The near-miss pairs are here rather than in one test file because two suites need them — the
boundary table of US5 and the matcher's own mechanism tests — and a second copy would drift.
"""

from __future__ import annotations

from hermes_memory.classification import ProjectRule, ProjectRuleSet

ALIAS = "orchard-pipeline"
"""A hyphenated alias. The hyphen is the interesting part: it is a word character here, which is
what makes `orchard-pipeline-ui` a miss (AM-2)."""

OTHER_ALIAS = "lantern"

SHORT_ALIAS = "op"
"""Short enough that a boundary rule is the only thing standing between it and every `option`."""


def rule(
    project: str = "orchard-pipeline",
    *aliases: str,
    priority: int = 0,
) -> ProjectRule:
    """One rule, defaulting to a single alias equal to the project name."""
    return ProjectRule(
        project=project,
        aliases=aliases or (project,),
        priority=priority,
    )


def rule_set(*rules: ProjectRule) -> ProjectRuleSet:
    """A rule set, defaulting to the one project most tests need."""
    return ProjectRuleSet(rules=rules or (rule(),))


def two_projects(*, first: int = 0, second: int = 0) -> ProjectRuleSet:
    """Two projects whose priorities a test chooses, for the ambiguity rules AR-3 and AR-4."""
    return ProjectRuleSet(
        rules=(
            rule("orchard-pipeline", ALIAS, priority=first),
            rule("lantern", OTHER_ALIAS, priority=second),
        )
    )


def document(*entries: str) -> str:
    """A TOML rule set, assembled from `[[project]]` blocks written by a test."""
    return "\n\n".join(entries) + "\n"


def entry(project: str, *aliases: str, priority: int | None = None) -> str:
    """One `[[project]]` block, with `priority` omitted entirely when it is not given."""
    rendered = ", ".join(f'"{alias}"' for alias in (aliases or (project,)))
    lines = [f'[[project]]\nproject = "{project}"\naliases = [{rendered}]']
    if priority is not None:
        lines.append(f"priority = {priority}")
    return "\n".join(lines)


HITS = (
    f"{ALIAS}",
    f"the {ALIAS} repo",
    f"nkz-soft/{ALIAS}",
    f"D:/Projects/nz/{ALIAS}",
    f"{ALIAS}.md",
    f"({ALIAS})",
    f"see {ALIAS}, then stop",
    f"a line ending in {ALIAS}",
)
"""Text in which `ALIAS` stands as a term. Each must match (AM-2)."""

MISSES = (
    f"{ALIAS}-ui",
    f"my-{ALIAS}",
    f"{ALIAS}s",
    f"x{ALIAS}",
    "orchard",
    "pipeline",
)
"""Text in which `ALIAS` does not stand as a term, or is only part of one. None may match (AM-2).

`orchard` and `pipeline` are here for the symmetry research R2 records: an alias is matched whole,
so a conversation naming only half of a hyphenated alias is a miss, and a user who wants both
spellings writes both.
"""

SHORT_HITS = (
    f"{SHORT_ALIAS}",
    f"the {SHORT_ALIAS} repo",
    f"{SHORT_ALIAS}/service",
)

SHORT_MISSES = (
    "option",
    "stop",
    f"{SHORT_ALIAS}s",
    f"{SHORT_ALIAS}-code",
)
"""`op-code` is a miss for the same reason `orchard-pipeline-ui` is: `-` is a word character."""
