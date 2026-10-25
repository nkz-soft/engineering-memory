# Implementation Plan: Project classifier

**Branch**: `010-project-classifier` | **Date**: 2026-10-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-project-classifier/spec.md` (issue #12)

## Summary

Implement `AliasProjectClassifier`, the first real implementation of the `ProjectClassifier`
boundary #9 declared, and with it ARCHITECTURE.md §15's level 2 — the only level available to the
MVP, because a ChatGPT export carries neither repository nor working directory and §21 puts
model-based classification out of scope.

The rules are the user's, in a TOML file read with `tomllib`: one entry per project, giving the
slug that becomes its `project:` tag, the literal aliases that identify it, and an integer priority.
Loading validates and may fail loudly; classifying cannot fail at all. All aliases compile into one
alternation, longest first, and a conversation's text-bearing fields — the same six #11's sanitizer
rewrites — are joined with a NUL and scanned once, so the text is read once rather than once per
rule. The NUL is not decoration: a line break is a boundary character, but the relaxed whitespace
of a multi-word alias consumes one, and the two rules together let an alias straddle the join
between two fields. A match requires a boundary at each of the alias's own word-character
edges under a word alphabet that includes `-`, so `nz` misses `nzxt` while `engineering-memory` misses
`engineering-memory-ui` and still hits `nkz-soft/engineering-memory`.

One project matched is the answer. Several resolve to the highest declared priority, and a tie at
the top resolves to `project:unknown` — a rule set that has not said which project wins does not
get a guess, and §15 already treats an unresolved project as an ordinary answer that stays
retrievable in the single shared bank (ADR-002). No rule set configured is a warning and an empty
rule set; a rule set configured and missing is a failure. `ChainedProjectClassifier` leaves §15's
third level a composition rather than a comment, and the MVP composes exactly one element.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: Pydantic v2 (#8's model, the rule set's validation), pydantic-settings
(#5's `Settings`), structlog (#6's logging, for two load-time records). Standard library `re` and
`tomllib`. **No new dependency** (research R1).

**Storage**: One file read, once, at construction: the rule set. Nothing is written. The classifier
itself touches no storage (research R6).

**Testing**: pytest. The contract suite `tests/contracts/classifier.py` (#9); unit tests for
matching, boundaries, resolution, loading, chaining and purity in `tests/unit/`; a structure test
that the matcher covers every text-bearing field of #8's model, and one that the module imports no
Hindsight, HTTP client or storage.

**Target Platform**: The developer machine and the container image (#7), Linux and Windows. The
path resolution of #5 is what makes `data/projects.toml` mean the same place on both.

**Performance Goals**: One compiled expression and one pass over the conversation's text, rather
than one pass per rule. Linear in the text **and** in the alias count — `re` does not build a trie
from a literal alternation, and research R4 records the measurements. At the scale a personal rule
set reaches this is tenths of a second for a very large conversation; no latency target, because
extraction dominates an import a person runs rarely (ADR-006).

**Constraints**: `classify` is deterministic, pure and total — no file, no socket, no clock, no
mutation, no exception (FR-008, FR-009, PC-5). No conversation content in a log record or an error
message (FR-014, Principle V). Aliases are literals, so no user input reaches a regular-expression
compiler as metasyntax (research R2).

**Scale/Scope**: a rule set of tens of projects and hundreds of aliases, run over every conversation
of a decade of personal history.

No item is left as NEEDS CLARIFICATION. The two questions the spec raised were answered by the user
before planning, and research.md R5 and R7 record them.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies |
|---|---|
| **I. Raw archive is the source of truth** | Classification neither reads nor writes the archive; it is handed a conversation and returns a tag. The one consequence worth stating is the one FR-012b makes the run state out loud: §17 skips unchanged conversations, so a tag written under an empty or incomplete rule set does not correct itself on a re-run. That is survivable precisely because Principle I keeps the originals — a reclassification pass over the archive is possible later, and is separate work. Nothing here forecloses it. |
| **II. Provenance and stable identity** | Determinism is the whole point: FR-008 and AR-6 make the same conversation and the same rules produce the same tag across calls, instances and runs, which is what keeps a re-import from filing one conversation under two projects. No clock is read (AR-7), identity fields are not scanned and not touched (AM-8), and the provenance's project is derived by the enrich stage from this tag rather than by classifying a second time (#9's research R7). |
| **III. Test-first** | Every id in contracts/rule-set.md — RS-1..13, AM-1..10, AR-1..9, CH-1..6 — gets its test written and observed failing before the code exists, as does each of #9's PC-1..5. The boundary-condition tests of AM-2 are written as a table of hits and misses, so the rule is pinned by examples before an expression is chosen to satisfy them. |
| **IV. Replaceable boundaries** | The implementation satisfies `ProjectClassifier` and adds nothing to the boundary: no new type crosses it, no signature changes, `classifier.py` is not edited. The module imports the normalized model, `re`, `tomllib` and structlog; it imports no Hindsight, no HTTP client and no storage layer, and a structure test enforces that. The one piece of I/O is in the loader, which is not the boundary and runs before the pipeline does — that split is what makes `classify` pure by construction rather than by discipline (research R6). Classification stays one stage, run conversation by conversation, so one failure cannot abort a run — and in fact it has no failure to isolate. |
| **V. Secrets never reach the memory engine** | Classification runs after sanitization in §7 and reads what the sanitizer returned. It logs nothing per conversation (AR-9, research R11), and the two load-time records carry a path and two counts. The rule set holds project names, repository names and paths — no credential — and its default location is under `data/`, which `.gitignore` already excludes, so the one personal file in this design cannot be committed to a public repository by accident (research R7). Test fixtures are synthesized (research R12). |

**Stack.** `re` and `tomllib` are the standard library; Pydantic, pydantic-settings, structlog and
pytest are already in the stack table. No dependency is added, so no decision record is required.
Promoting `pyyaml` from a development dependency would have required one, which is part of why the
rule set is TOML (research R1).

**Governance impact.** None. Issue #12 ticks "None of the above": no principle changes, the stack is
untouched, the Hindsight contract and the bank strategy are not involved, and no history source is
added. The tag convention is **consumed** as §6 fixes it — one `project:` tag per conversation, slug
validated by the existing `ProjectTag` — and not amended. Emitting several project tags would have
amended it, which is why the spec rules it out as an assumption rather than treating it as an
option.

**Gate result: PASS.** No deviation to justify; Complexity Tracking is therefore empty and omitted.

**Re-check after Phase 1 design: PASS.** The design adds five modules inside `classification`, one
public classifier plus a chain, one error type and one settings field. Three consequences are
recorded rather than hidden. First, R5's deliberate refusal: a conversation genuinely about two
equally-ranked projects is filed under neither, and a person who wants it filed must express a
preference in the rule set. Second, R7's asymmetry: the default location warns and the configured
one fails, which means a user who deletes their rules file while keeping the setting gets an error
and a user who never had one gets a warning — intended, and visible in the output of both. Third,
R2's alphabet: treating `-` as a word character is the choice that makes `engineering-memory-ui` a miss,
and it is also what makes an alias `hermes` miss `engineering-memory`. A user who wants both writes both,
which is the behaviour AM-5 already commits to.

## Alternatives considered

- **Asking a model to classify each conversation** (named in issue #12). Out of scope by §21, and
  wrong on its own terms: §17 requires re-import to be idempotent, and a classifier that answers
  differently on the second run files the same conversation under two projects. It would also send
  the content out of the process, which Principle V constrains, and make every import pay extraction
  cost twice.
- **File order as priority.** Rejected: a diff that moves a block would reclassify history, and the
  rule would be invisible to anyone reading one entry rather than the whole file (research R5).
- **Longest matched alias wins across projects.** Rejected as a *resolution* rule: unpredictable
  when two aliases are of similar length, and it rewards verbose aliases. It is kept as a *matching*
  rule — AM-6 — where it does something defensible: attributing one position to the more specific
  alias.
- **Scoring by number of occurrences.** Rejected: repetition is an artifact of how someone typed and
  of how the parser split the text, not evidence of subject.
- **Emitting a `project:` tag per matched project.** Rejected: §6 gives one project namespace and
  #9's boundary returns one tag; changing that is a change to the tag convention, which Governance
  puts behind a decision record.
- **YAML for the rule set.** Rejected: `pyyaml` is a development dependency today, promoting it
  needs a decision record, and YAML's implicit typing would read the alias `no` as a boolean
  (research R1).
- **Refusing to run without a rule set.** Put to the user as Question 2 option B and not chosen. It
  would also block #22's dry run behind the configuration that run exists to avoid.
- **An empty rule set accepted silently.** Rejected: it is the quiet failure this repository
  consistently refuses, and the damage — an entire corpus tagged `project:unknown` — surfaces months
  later (FR-012a).
- **`\b` for the alias boundary.** Rejected: `\b` is defined over `\w`, which excludes `-`, so
  `engineering-memory` would match inside `engineering-memory-ui` (research R2).
- **A `fallback` parameter on the alias classifier instead of a chain.** Rejected: it makes one
  implementation the owner of §15's ordering, and the level that arrives first in practice is level
  1, which belongs *ahead* of the alias rules (research R8).
- **Raising a `BoundaryError` for a bad rule set.** Rejected: #19's per-conversation isolation would
  catch it, turning one misconfiguration into tens of thousands of identical failures (research R6).
- **A debug log record per classification.** Rejected: one record per conversation over a corpus
  this size, duplicating what #19 already reports, and it would tempt a maintainer to log the
  matched alias, which is conversation content (research R11).

## Project Structure

### Documentation (this feature)

```text
specs/010-project-classifier/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── rule-set.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks, after the gate
```

### Source Code (repository root)

```text
src/engineering_memory/classification/
├── __init__.py            # public surface: #9's boundary types plus the classifiers and the loader
├── classifier.py          # #9's protocol and UNKNOWN_PROJECT — UNCHANGED by this feature
├── rules.py               # ProjectRule, ProjectRuleSet, ProjectRulesError (RS-5..RS-12)
├── loader.py              # path resolution, tomllib, error translation, the two records (RS-1..4, RS-13)
├── matcher.py             # the compiled alternation and the single scan (AM-1..AM-7, AM-10)
├── alias_classifier.py    # AliasProjectClassifier: the field sweep and the priority resolution (AM-8..9, AR-1..9)
└── chain.py               # ChainedProjectClassifier: the §15 seam (CH-1..6)

src/engineering_memory/
└── settings.py            # extended: project_rules_path (#5's resolution rules)

tests/
├── unit/
│   ├── test_alias_matching.py            # the six placements, case folding, whitespace (SC-001)
│   ├── test_alias_boundaries.py          # the hit/miss table of AM-2, AM-3, AM-6, AM-7 (SC-005)
│   ├── test_project_resolution.py        # AR-1..AR-6, repetition and file order (SC-003)
│   ├── test_project_rules.py             # ProjectRuleSet validation: RS-5..RS-11
│   ├── test_project_rules_loading.py     # paths, tomllib, the warning and the failure (SC-004, SC-004a)
│   ├── test_classifier_chain.py          # CH-1..CH-5 (SC-006)
│   ├── test_classification_is_pure.py    # no file, no socket, no clock, no log (AR-7, AR-9, SC-008)
│   └── test_settings_project_rules.py    # the new field and its resolution (#5's rules)
├── structure/
│   ├── test_matcher_covers_the_model.py  # every text-bearing field of #8 is swept (AM-8, research R10)
│   └── test_classification_imports.py    # no Hindsight, no HTTP, no storage (Principle IV)
├── contracts/
│   └── test_alias_classifier_passes_the_contract.py  # #9's PC-1..PC-5, none skipped (SC-007)
└── synthetic/
    └── projects.py                       # synthesized rule sets and project names (research R12)

projects.example.toml      # the documented format, mirroring .env.example
.env.example               # extended: ENGINEERING_MEMORY_PROJECT_RULES_PATH
```

**Structure Decision**: the constitution's module tree fixes `classification`; this feature fills
it. The split inside the module follows what is separately testable and what fails separately —
whether a rule set is well-formed (`rules`), whether a file becomes one (`loader`), whether a string
names a project (`matcher`), and whether matches become a tag (`alias_classifier`) — and it puts
every piece of I/O in `loader`, which is what lets `classify` be pure by construction. #9's
declaration in `classifier.py` is left untouched, so the boundary stays readable as a boundary
rather than as the first implementation of one. It is the shape #11 used for `sanitization`, for the
same reasons.
