"""§15's levels, in order, without any level knowing about the others.

ARCHITECTURE.md §15 lists three ways to determine a project: explicit metadata, deterministic
alias rules, and model-based classification — the last out of scope by §21. This is where they
attach to each other, and it exists now, with one element, so that adding another later is a
composition rather than a rewrite of the one that was there first.

The level that will arrive first is not the third but the first: Claude Code and Codex sessions
carry a repository and a working directory (#27, #28), and a classifier reading those belongs
*ahead* of the alias rules. A `fallback` argument on `AliasProjectClassifier` would have made one
implementation the owner of that ordering, and nesting two more into it is how a composition
becomes a tangle (specs/010-project-classifier/research.md R8).

"Resolved" is the absence of `UNKNOWN_PROJECT`, not a `None` an element returns: #9 refused a
second spelling of the §15 answer, and this module does not reintroduce one.
"""

from __future__ import annotations

from collections.abc import Sequence

from engineering_memory.classification.classifier import UNKNOWN_PROJECT, ProjectClassifier
from engineering_memory.normalization import Conversation, ProjectTag

__all__ = ["ChainedProjectClassifier"]


class ChainedProjectClassifier:
    """Asks each classifier in turn and takes the first answer that is not `project:unknown`."""

    def __init__(self, classifiers: Sequence[ProjectClassifier]) -> None:
        self._classifiers = tuple(classifiers)

    def classify(self, conversation: Conversation) -> ProjectTag:
        """The first resolved answer, or `UNKNOWN_PROJECT` when none of them resolved one.

        A later element is not consulted once one has answered — which matters for the level this
        seam was left for, since asking a model is the expensive thing the cheap rules exist to
        avoid.
        """
        for classifier in self._classifiers:
            answered = classifier.classify(conversation)
            if answered != UNKNOWN_PROJECT:
                return answered

        return UNKNOWN_PROJECT
