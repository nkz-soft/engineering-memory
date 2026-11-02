"""§15 level 1: classify recorded context without inspecting a live checkout."""

import re
from urllib.parse import urlsplit

from engineering_memory.classification.alias_classifier import AliasProjectClassifier
from engineering_memory.classification.classifier import UNKNOWN_PROJECT
from engineering_memory.classification.rules import ProjectRuleSet
from engineering_memory.normalization import Conversation, ProjectTag


class MetadataProjectClassifier:
    def __init__(self, rules: ProjectRuleSet):
        self._aliases = AliasProjectClassifier(rules)

    def classify(self, conversation: Conversation) -> ProjectTag:
        for context in (conversation.repository, conversation.working_directory):
            if not context:
                continue
            # Only the source context participates here. Prose belongs to the next chain element.
            projected = conversation.model_copy(update={"title": context, "messages": ()})
            mapped = self._aliases.classify(projected)
            if mapped != UNKNOWN_PROJECT:
                return mapped
            try:
                path = urlsplit(context).path if "://" in context else context
            except ValueError:
                continue
            basename = path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
            basename = basename.rsplit(":", 1)[-1].removesuffix(".git")
            slug = re.sub("[^a-z0-9._-]+", "-", basename.lower()).strip("-._")
            if slug and slug != "unknown":
                return ProjectTag(value=slug)
        return UNKNOWN_PROJECT
