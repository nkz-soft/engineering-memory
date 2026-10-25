"""Determine the project a conversation belongs to.

The project classifier boundary of ARCHITECTURE.md §8, the §15 answer for a conversation no rule
matches, and the alias rules that decide the rest (#12).

What a caller needs is three things: `load_project_rules` to read the user's file,
`AliasProjectClassifier` to answer from it, and `ChainedProjectClassifier` for the day §15's other
levels exist — explicit metadata ahead of the rules when a source carries a repository (#27, #28),
model-based classification behind them if §21 ever permits it.

Nothing here raises while classifying. Everything that can be wrong about a rule set is refused
when it is loaded, which is what lets `classify` be total (PC-5, contracts/errors.md E8).
"""

from engineering_memory.classification.alias_classifier import AliasProjectClassifier
from engineering_memory.classification.chain import ChainedProjectClassifier
from engineering_memory.classification.classifier import UNKNOWN_PROJECT, ProjectClassifier
from engineering_memory.classification.loader import load_project_rules
from engineering_memory.classification.rules import ProjectRule, ProjectRulesError, ProjectRuleSet

__all__ = [
    "UNKNOWN_PROJECT",
    "AliasProjectClassifier",
    "ChainedProjectClassifier",
    "ProjectClassifier",
    "ProjectRule",
    "ProjectRuleSet",
    "ProjectRulesError",
    "load_project_rules",
]
