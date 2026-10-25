# Contract: the project rule set and how it classifies

**Feature**: 010-project-classifier (issue #12)

Two contracts are described here. The first is the configuration file a user writes — a public
surface, in the sense that changing it breaks someone's setup. The second is the behaviour the
implementation owes: the matching rules, the resolution rule, and the loading rules. Each is given
an id, and each id gets a test.

This feature satisfies, and does not amend, the `ProjectClassifier` contract of
`specs/007-boundary-interfaces/contracts/contract-suites.md` (PC-1 to PC-5).

## The configuration file

TOML, read with `tomllib` (research R1). One array-of-tables entry per project:

```toml
# projects.example.toml — copy to data/projects.toml and make it yours.

[[project]]
project = "engineering-memory"
aliases = ["engineering-memory", "nkz-soft/engineering-memory", "engineering memory"]
priority = 10

[[project]]
project = "atlas"
aliases = ["atlas", "atlas-api", "D:/Projects/atlas"]
# priority omitted: defaults to 0
```

| Key | Required | Type | Meaning |
|---|---|---|---|
| `project` | yes | string | the slug that becomes `project:<slug>`; must satisfy §6's slug shape |
| `aliases` | yes | array of strings | the literal terms that identify this project; at least one |
| `priority` | no | integer | decides an ambiguous conversation; higher wins; defaults to `0` |

No other key is permitted, at either level: a misspelled `alias` or `prioirty` is a rule that
silently does less than its author meant, and a strict read turns it into a message naming the key.

## Loading rules

| Id | Rule |
|---|---|
| RS-1 | The location comes from `ENGINEERING_MEMORY_PROJECT_RULES_PATH`, defaulting to `data/projects.toml`, relative paths resolved against the repository root as in #5. |
| RS-2 | A path given explicitly with nothing at it is a failure naming that path. |
| RS-3 | No path given and nothing at the default location is **not** a failure: the rule set is empty, and one warning names the path looked at, states that every conversation this run will be `project:unknown`, and states that §17 will not revisit them (FR-012a, FR-012b). |
| RS-4 | A file that is not valid TOML is a failure naming the file and the parser's complaint. |
| RS-5 | A file valid as TOML but not as a rule set — a missing `project`, an unknown key, a `priority` that is not an integer — is a failure naming the offending entry. |
| RS-6 | A `project` that is not a valid §6 slug is a failure naming it. |
| RS-7 | The `project` slug `unknown` is a failure: it is indistinguishable from the no-match answer. |
| RS-8 | A project declared twice is a failure naming it. |
| RS-9 | An alias that is empty, or that contains no letter and no digit, is a failure naming it and its project. |
| RS-10 | One alias declared by two projects is a failure naming the alias and both projects; comparison is case-insensitive. |
| RS-11 | A file holding no project at all loads as an empty rule set, without a warning: writing an empty file is a choice, unlike not writing one. |
| RS-12 | Every failure is a `ProjectRulesError`, which is **not** a `BoundaryError` (research R6). |
| RS-13 | Loading emits one `info` record naming the path, the project count and the alias count; neither it nor RS-3's warning carries conversation content. |

## Matching rules

Applied to the text-bearing fields of #8's model: `Conversation.title`, each `Message.text`, each
`ToolActivity.name`, `.request` and `.result`, each `NonTextPart.name` (FR-005, research R10).

| Id | Rule |
|---|---|
| AM-1 | Matching is case-insensitive, by case folding rather than by lowercasing, so non-ASCII aliases behave. |
| AM-2 | An alias matches only where each of its own edges that is a word character sits against a non-word character or the end of the text. A word character is a letter, a digit, `_` or `-`; everything else is a boundary (research R2). |
| AM-3 | An edge of an alias that is not itself a word character imposes no constraint on that side. |
| AM-4 | A run of whitespace inside an alias matches any non-empty run of whitespace in the text, line breaks included (research R3). |
| AM-5 | An alias is a literal. No character in it is metasyntax, and a rule set cannot express a pattern. |
| AM-6 | Where two aliases could match at one position, the longer one does, so a match is attributed to the project whose alias is more specific (research R4). |
| AM-7 | No alias may match across the join between two fields. |
| AM-8 | Identity fields — `source`, `source_id`, the derived `document_id` — and timestamps are not scanned. |
| AM-9 | A conversation with no title, no messages, or no text at all is matched against, and matches nothing. |
| AM-10 | How often an alias occurs is not recorded and does not affect the outcome. |

## Resolution rules

| Id | Rule |
|---|---|
| AR-1 | No project matched → `UNKNOWN_PROJECT`. |
| AR-2 | Exactly one project matched → that project's `ProjectTag`, whatever its priority. |
| AR-3 | Several projects matched → the one with the highest `priority`. |
| AR-4 | Several projects matched sharing the highest `priority` → `UNKNOWN_PROJECT` (research R5). |
| AR-5 | Several aliases of one project matched → that project; this is not ambiguity. |
| AR-6 | The outcome does not depend on the order rules appear in the file, on any iteration order, or on how many conversations were classified before. |
| AR-7 | `classify` reads no file, opens no socket, consults no clock, and leaves the conversation it was handed unchanged. |
| AR-8 | `classify` raises nothing — not `ProjectRulesError`, not `BoundaryError`, not anything else (PC-5). |
| AR-9 | `classify` emits no log record (research R11). |

## Chaining rules

| Id | Rule |
|---|---|
| CH-1 | A chain returns the first element's answer that is not `UNKNOWN_PROJECT`. |
| CH-2 | An element after the first resolved answer is not consulted. |
| CH-3 | A chain in which every element resolves nothing returns `UNKNOWN_PROJECT`. |
| CH-4 | An empty chain returns `UNKNOWN_PROJECT`. |
| CH-5 | A chain satisfies `ProjectClassifier` and passes PC-1 to PC-5 itself. |
| CH-6 | Nothing in the MVP's assembled pipeline places a model-based classifier in a chain (§21). **Deferred to #19**: no pipeline is assembled yet, so what stands here instead is a static guard — `tests/structure/test_classification_imports.py` refuses an import of any model SDK from this package. #19 inherits the rule. |

## What a conforming implementation must also do

Pass `ProjectClassifierContract` from `tests/contracts/classifier.py` unchanged, with the rule set
the suite's conversations do not match — which is what makes PC-2 meaningful rather than
accidental.
