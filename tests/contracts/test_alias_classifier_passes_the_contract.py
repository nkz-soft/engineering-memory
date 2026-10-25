"""The alias classifier against the project-classifier contract, PC-1 to PC-5.

The rule set handed to the suite is deliberately **not** empty. An empty one would pass PC-2 for
the wrong reason — a classifier that resolves nothing resolves nothing for every conversation,
including the one the rule says must come back `project:unknown`. With real rules loaded and the
suite's synthesized conversations naming none of them, PC-2 proves what it is for: that a
*working* classifier treats an unresolved project as an answer rather than a failure.

The suite's conversations talk about a saga, Wolverine, a duck and an `app.log`; the rules here
name invented projects (`tests/synthetic/projects.py`). Neither file knows about the other, which
is what keeps the non-match honest.
"""

from __future__ import annotations

from engineering_memory.classification import ProjectClassifier
from engineering_memory.classification.alias_classifier import AliasProjectClassifier
from tests.contracts.classifier import ProjectClassifierContract
from tests.synthetic import projects


class TestAliasProjectClassifier(ProjectClassifierContract):
    def make_classifier(self) -> ProjectClassifier:
        return AliasProjectClassifier(projects.two_projects(first=10, second=5))

    def test_the_rule_set_is_not_empty(self) -> None:
        """Otherwise PC-2 would hold because nothing could ever match (SC-007)."""
        assert projects.two_projects().rules

    def test_the_suites_conversations_name_none_of_these_projects(self) -> None:
        """The non-match is a property of the fixtures, asserted rather than assumed."""
        classifier = self.make_classifier()

        for conversation in self.classifiable_conversations():
            assert str(classifier.classify(conversation)) == "project:unknown"
