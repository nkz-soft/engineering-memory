# Data model: Project classifier

**Feature**: 010-project-classifier (issue #12)

This feature adds no type that crosses a boundary. What crosses is #9's: a `Conversation` in, a
`ProjectTag` out. The types below are internal to `engineering_memory.classification`, and are described
here because they are where the rules of [contracts/rule-set.md](./contracts/rule-set.md) live.

## Types that already exist and are used unchanged

| Type | Declared in | Role here |
|---|---|---|
| `Conversation`, `Message`, `ToolActivity`, `NonTextPart` | `engineering_memory.normalization` (#8) | the input, and the text-bearing fields R10 enumerates |
| `ProjectTag` | `engineering_memory.normalization.tags` (#8) | the answer; its `Slug` is what validates a rule's project name |
| `ProjectClassifier` | `engineering_memory.classification.classifier` (#9) | the protocol this feature satisfies |
| `UNKNOWN_PROJECT` | same | the §15 answer, returned on no match and on a top-priority tie |
| `Settings` | `engineering_memory.settings` (#5) | gains one field; see below |

None of these is edited except `Settings`, which gains `project_rules_path`.

## `ProjectRule`

One project, as the configuration declares it. A frozen Pydantic model.

| Field | Meaning |
|---|---|
| `project` | the `Slug` that becomes the `project:` tag's value |
| `aliases` | the literal terms that identify it; at least one, each containing a letter or a digit |
| `priority` | an integer, defaulting to `0`; higher wins an ambiguous conversation (R5) |

`priority` is a field rather than the rule's position in the file, so that reordering the
configuration cannot reclassify history. It is permitted to collide: two projects at the same
priority is how a rule set says "equally plausible", and FR-007 turns that into `project:unknown`
rather than into a guess.

The slug `unknown` is refused: it would be indistinguishable from the no-match answer, and a rule
that cannot be told from the absence of a rule is a trap rather than a shorthand.

## `ProjectRuleSet`

The validated collection a classifier is built from. Frozen.

| Field | Meaning |
|---|---|
| `rules` | the project rules, in no significant order |

Validation belongs here rather than to classification, because this is the moment failing loudly is
allowed (R6). What it refuses, each naming the offending entry: a duplicate project, an alias
claimed by two projects, an alias that is empty or holds no letter or digit, a priority of the
wrong kind, and the reserved slug. An empty rule set is **valid** — it is what FR-012a builds when
no rules were configured, and it classifies everything as `project:unknown`.

Case is not part of an alias's identity: `engineering-memory` and `engineering-memory` are the same alias, so
two projects declaring them collide and the rule set is refused.

## `AliasMatcher` (internal)

The compiled form of a rule set: one alternation over every alias, longest first, plus the map from
casefolded alias to project (R4). It is built once per rule set and answers "which projects does
this text name" in one pass.

It holds no state between calls and never sees a `Conversation` — it is handed text. That is what
keeps the field enumeration of R10 in one place, in the classifier, where the structure test can
see it.

## `AliasProjectClassifier`

The implementation of #9's protocol. Built from a `ProjectRuleSet`; holds an `AliasMatcher`.

`classify` gathers the text-bearing fields, asks the matcher which projects are named, and resolves:
no project → `UNKNOWN_PROJECT`; one project → its tag; several → the highest priority, or
`UNKNOWN_PROJECT` if the highest is shared. It reads no file, consults no clock, makes no network
call, mutates nothing and raises nothing.

## `ChainedProjectClassifier`

Also an implementation of #9's protocol, holding an ordered sequence of them (R8). It returns the
first answer that is not `UNKNOWN_PROJECT`, and `UNKNOWN_PROJECT` when none is. With one element it
is that element; with none it is a classifier that resolves nothing, which is a legitimate thing to
build and a cheap test.

This is §15's ordering expressed as composition: level 1 ahead of level 2 when a source carries
metadata (#27, #28), level 3 behind level 2 if it is ever in scope (§21).

## `ProjectRulesError`

Raised by the loader when a rule set cannot be read, parsed or validated. A `RuntimeError`, and
deliberately **not** a `BoundaryError`: #19's per-conversation isolation catches `BoundaryError`,
and a misconfigured run must stop once rather than fail identically tens of thousands of times
(R6).

Its message names the path and the offending entry. It does not quote conversation content, because
it has never seen any — loading happens before any conversation is read.

## `Settings.project_rules_path`

| Field | Type | Default |
|---|---|---|
| `project_rules_path` | `Path` | `data/projects.toml` |

Resolved against the repository root like `archive_root` and `import_state_path` (#5, FR-013 of that
feature), so the same value means the same place wherever a command is run from. Documented in
`.env.example` as `ENGINEERING_MEMORY_PROJECT_RULES_PATH`; the test #5 left standing fails if it is not.

The field cannot by itself say whether the operator chose the path or inherited it, and FR-012a
needs that distinction. The loader asks the settings object which fields were explicitly set rather
than comparing the value to the default — a user who sets the path to exactly `data/projects.toml`
has still chosen it, and should get the failure rather than the warning.

## What this feature does not model

- **A project's description, repository URL, or anything else about it.** The rule set is matching
  rules, not a project registry. A field nothing reads is a field the next format change has to
  carry.
- **Per-source rules.** §15 level 1 applies to sources that carry metadata; that arrives with those
  sources (#27, #28), composed through the chain rather than configured here.
- **Patterns.** R2: aliases are literals.
- **The `type:` tag.** §6 names its vocabulary and nothing yet assigns it; this feature does not
  start.
- **Provenance.** The enrich stage of §7 derives the provenance's project from the tag (#9's
  research R7); classification returns the tag and stops.
