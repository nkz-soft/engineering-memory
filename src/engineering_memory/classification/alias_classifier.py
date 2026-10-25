"""§15's level 2: the project a conversation names, decided by rules a person wrote.

The implementation of #9's `ProjectClassifier` boundary, and the one the MVP runs. Level 1 —
explicit metadata — does not apply to a ChatGPT export, which carries neither repository nor
working directory; level 3 is out of scope by §21 and attaches through `chain.py` when it is not.

`classify` is total: every conversation gets a tag, nothing is raised, nothing is read from disk
or the network, no clock is consulted, and the conversation handed in is not touched. That is not
restraint, it is construction — everything that can fail was spent when the rule set was built
(specs/010-project-classifier/research.md R6).

`SWEPT_FIELDS` and `IGNORED_FIELDS` name the fields of #8's model rather than walking every string
in it, so that a native identifier coinciding with an alias cannot file a conversation under a
project it never mentioned. `tests/structure/test_matcher_covers_the_model.py` holds the lists to
the model, and to the sanitizer's — the two stages of §7 that read text must read the same text.
"""

from __future__ import annotations

from engineering_memory.classification.classifier import UNKNOWN_PROJECT
from engineering_memory.classification.matcher import AliasMatcher
from engineering_memory.classification.rules import ProjectRuleSet
from engineering_memory.normalization import Conversation, ProjectTag

__all__ = ["IGNORED_FIELDS", "SWEPT_FIELDS", "AliasProjectClassifier"]

SWEPT_FIELDS: dict[str, frozenset[str]] = {
    "Conversation": frozenset({"title", "messages"}),
    "Message": frozenset({"text", "tool_activity", "non_text_parts"}),
    "ToolActivity": frozenset({"name", "request", "result"}),
    "NonTextPart": frozenset({"name"}),
}
"""Fields that carry text a person or a tool wrote — or that hold models which do."""

IGNORED_FIELDS: dict[str, frozenset[str]] = {
    "Conversation": frozenset({"source", "source_id", "started_at", "last_activity_at"}),
    "Message": frozenset({"role", "sent_at"}),
    "ToolActivity": frozenset(),
    "NonTextPart": frozenset({"kind"}),
}
"""Identity, time and closed vocabularies. Never swept (AM-8)."""

_JOIN = "\x00"
"""What separates two fields in the swept text, and the reason AM-7 holds.

A line break was the obvious choice and was wrong, which is worth recording where the choice is
made rather than only in the research. A newline is a boundary character, so it satisfies AM-2 —
but AM-4 relaxes the whitespace inside a multi-word alias to one-or-more whitespace, and that
consumes a newline happily. Composed, the two rules produced exactly what AM-7 forbids: with the
alias `engineering memory`, a title ending "we discussed engineering" beside a message beginning
"memory layouts" forged a match that existed in neither field.

NUL is a boundary character that no whitespace class matches, so it separates fields for AM-2 and
blocks them for AM-4. A NUL occurring in a conversation's own text is harmless in the direction
that matters: it can only stop a match, never forge one.
"""


class AliasProjectClassifier:
    """Decides a conversation's project from a rule set of literal aliases."""

    def __init__(self, rules: ProjectRuleSet) -> None:
        self._priority_of = {rule.project: rule.priority for rule in rules.rules}
        self._matcher = AliasMatcher(rules)

    def classify(self, conversation: Conversation) -> ProjectTag:
        named = self._matcher.projects_named(_sweep(conversation))

        if not named:
            return UNKNOWN_PROJECT

        if len(named) == 1:
            return ProjectTag(value=next(iter(named)))

        return self._resolve(named)

    def _resolve(self, named: frozenset[str]) -> ProjectTag:
        """Several projects named: the highest declared priority wins, a tie at the top does not.

        A rule set in which two projects are equally plausible has not said which one wins, so
        neither does this. `project:unknown` keeps the conversation imported and retrievable —
        possible precisely because there is one shared bank (ADR-002) — where a guess would produce
        a confident wrong tag that nobody filtering by `project:` could detect (research R5).
        """
        highest = max(self._priority_of[project] for project in named)
        tied = [project for project in named if self._priority_of[project] == highest]

        if len(tied) > 1:
            return UNKNOWN_PROJECT

        return ProjectTag(value=tied[0])


def _sweep(conversation: Conversation) -> str:
    """The conversation's text, in the fields `SWEPT_FIELDS` names, joined by a boundary."""
    parts: list[str] = []

    if conversation.title is not None:
        parts.append(conversation.title)

    for message in conversation.messages:
        parts.append(message.text)
        for activity in message.tool_activity:
            parts.append(activity.name)
            if activity.request is not None:
                parts.append(activity.request)
            if activity.result is not None:
                parts.append(activity.result)
        for part in message.non_text_parts:
            if part.name is not None:
                parts.append(part.name)

    return _JOIN.join(parts)
