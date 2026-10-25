# Research: Project classifier

**Feature**: 010-project-classifier (issue #12) | **Date**: 2026-10-25

Every decision here is settled from ARCHITECTURE.md §§6, 8, 15, 17, 21, ADR-002, the constitution's
Principles I–V, the boundary #9 already declares, the model #8 already declares and the settings #5
already declares. The two questions the specification raised were put to the user and answered
before planning: priority decides ambiguity and a tie at the top yields `project:unknown` (R5), and
an unconfigured rule set warns rather than fails (R7). Nothing is left as NEEDS CLARIFICATION.

## R1 — The rule set is a TOML file, read with the standard library

**Decision**: the rules live in a TOML document, parsed with `tomllib` from the standard library
and validated into Pydantic models. No new dependency.

**Rationale**: the stack table fixes the dependencies and adding one needs a decision record
(constitution, Additional Constraints). YAML is the reflex for a file like this and it would cost
exactly that record: `pyyaml` is currently a **development** dependency, pinned for pattern-matching
the CI workflow's text, and promoting it to a runtime dependency is not a side effect a feature gets
to have. `tomllib` is in the standard library of the Python 3.13 the stack already fixes, the
repository already keeps its configuration in TOML (`pyproject.toml`), and the shape needed here —
a table per project with a list of strings and an integer — is TOML's plainest form.

**Alternatives considered**: YAML — rejected above, and its implicit typing would turn an alias like
`no`, `on` or `1.10` into a boolean or a float before validation ever saw it, which is a silent
mis-read of a user's project name. JSON — no comments, and a rule set is a file a person maintains
by hand and annotates. The `.env` file of #5 — a list of projects each with several aliases and a
priority is not a flat key-value namespace, and forcing it into one produces
`HERMES_PROJECT_RULES__0__ALIASES__2` and a file nobody edits twice. Python module as
configuration — executable configuration in a tool that reads a decade of private history is a
liability out of all proportion to the convenience.

## R2 — Aliases are literal terms, matched at a boundary the repository defines itself

**Decision**: an alias is a literal string, never a pattern. It matches case-insensitively, and only
where each of its own edges that is a *word character* sits against a non-word character or the end
of the text. A word character here is a letter, a digit, `_` or `-`; everything else — whitespace,
`/`, `\`, `.`, `:`, quotes, brackets, punctuation — is a boundary.

**Rationale**: the specification's FR-004 and Story 5 fix the behaviour; the question research has
to settle is what "boundary" means, and the obvious answer is wrong here. Python's `\b` is defined
over `\w`, which does **not** include `-`. Under `\b`, the alias `hermes-memory` matches inside
`hermes-memory-ui`, which Story 5 scenario 3 forbids. Treating `-` as a word character fixes that
and keeps the three cases the stories demand: `nz` does not match `nzxt` (a letter follows), `nz`
matches `nz/hermes-memory` (`/` is a boundary) and `the nz repo` (space is a boundary), and
`hermes-memory` matches inside `nkz-soft/hermes-memory` (`/` precedes).

The constraint is applied per edge, and only where the alias's own edge character is a word
character. An alias that ends in a boundary character of its own — `nkz-soft/` — would otherwise
demand two boundaries in a row and never match anything.

Patterns are refused outright. A regular expression in a configuration file is a second language to
specify, to validate and to defend: catastrophic backtracking over a corpus of a decade of history
is a hang, not an error message, and the issue asks for names, paths and aliases, all of which are
literals. A user who needs two spellings writes two aliases.

**Alternatives considered**: `\b` — rejected above. Substring matching with no boundary at all —
rejected: a project called `api` would claim every conversation containing `rapid`, and the damage
is silent misfiling, which is worse than a miss (§15 already treats a miss as ordinary). Token
splitting of the text, then set membership — rejected: it needs a tokenizer that agrees with the
alias writer about `nkz-soft/hermes-memory`, and the disagreement surfaces as a rule that mystifies.

## R3 — Whitespace inside an alias matches any run of whitespace

**Decision**: when an alias contains whitespace, each run of whitespace in it matches any non-empty
run of whitespace in the text, line breaks included.

**Rationale**: Story 5 scenario 4 requires `engineering memory` to match across a line break. A
multi-word alias is how a person names a project in prose, and prose wraps. Treating the alias's
space as a literal single space would make the rule depend on where the text happened to break —
an artifact of the export, not of what was written.

**Alternatives considered**: normalizing all whitespace in the text to single spaces before matching
— rejected: it means building a second copy of every conversation's text, and it would make
positions meaningless if a later feature ever wants them.

## R4 — One compiled alternation, one pass over the text

**Decision**: all aliases of all projects are compiled into a single alternation, longest alias
first, and the conversation's text-bearing fields are joined with a line break and scanned once.
Each match is mapped back to its project through a dictionary keyed by the casefolded alias.

**Rationale**: the corpus is a decade of history and the scan runs per conversation, so cost should
be bounded by the text rather than by the number of projects. One pass over the text with one
compiled expression gives that; a loop of "for each rule, search the text" gives the opposite, and
the spec's assumptions already promise the first.

Longest-first ordering matters because `re`'s alternation is leftmost-first rather than
leftmost-longest: without it, at a position where both `nz` and `nz/hermes-memory` could match, the
shorter alias would win and the match would be attributed to the wrong project. The mapping back is
unambiguous because FR-010 refuses a rule set in which two projects declare the same alias.

Joining the fields with `\n` rather than concatenating them is what keeps a title ending in `herm`
and a first message beginning `es-memory` from forging a match: `\n` is a boundary character, so no
alias can straddle the join.

**Alternatives considered**: named groups, one per project — rejected: the slugs would have to be
mangled into Python identifiers and back, for no gain over a dictionary. Scanning each field
separately — equivalent in result and marginally slower; the join is simpler to reason about and
makes the "no straddling" property one assertion rather than one per field. Aho–Corasick via a new
dependency — rejected: a decision record for a scale this feature does not have.

## R5 — Ambiguity: declared priority decides, a tie at the top does not

**Decision** (the user's answer to Question 1): every project rule carries an integer `priority`,
defaulting to `0`, higher wins. A conversation matching several projects resolves to the matching
project with the highest priority. Where two or more matching projects share the highest priority,
the result is `UNKNOWN_PROJECT`.

**Rationale**: §17 makes idempotency a requirement, so the answer must not depend on anything that
can vary between runs — not dictionary order, not file order, not how many times a word occurred.
A declared integer is the one input that is visible in the rule set, stable across runs, and
predictable by the person who wrote it. Declaring it rather than inferring it from the rule's
position means moving a block in the file cannot change how a conversation is filed.

The tie is deliberately not broken. A rule set in which two projects are equally plausible has not
said which one wins, and §15 already has a word for "this conversation does not resolve to a
project" — one that keeps the conversation imported and retrievable, because there is one shared
bank (ADR-002). Inventing a preference would produce a confident wrong tag, which is the one
outcome a person filtering by `project:` cannot detect.

A conversation matching two aliases of the *same* project is not ambiguity and never reaches this
rule.

**Alternatives considered**: file order as priority — rejected: it makes a diff that moves a block
change the classification of history. Longest matched alias wins across projects — rejected: it
reads as a rule that cannot be predicted when two aliases are of similar length, and it quietly
rewards verbose aliases. Scoring by number of occurrences — rejected: repetition is an artifact of
how someone typed, and it would make the outcome depend on the parser. Emitting both tags —
rejected: §6 gives one `project:` namespace and #9's boundary returns one tag; changing that is a
change to the tag convention, which Governance puts behind a decision record.

## R6 — Loading is where failure is allowed to be loud; classifying is not

**Decision**: validation and I/O live in a loader, which raises `ProjectRulesError` — a
`RuntimeError`, deliberately **not** a `BoundaryError`. The classifier is constructed from an
already-valid rule set, and `classify` therefore performs no I/O and has no failure path at all.

**Rationale**: the two obligations look contradictory and are not. PC-5 and contracts/errors.md E8
say this boundary declares no error; FR-010 and FR-011 say a broken rule set must fail loudly. They
are about different moments. Putting every file read, parse and validation at construction makes
`classify` pure by construction rather than by discipline — FR-009's "no file read, no network, no
clock" is then a property of a function that has nothing to read from.

`ProjectRulesError` is not a `BoundaryError` for the same reason: a subclass would be catchable by
the pipeline's per-conversation error isolation (#19), which would turn a misconfigured run into
thousands of identical per-conversation failures instead of one refusal before the run starts.

**Alternatives considered**: validating lazily on first use — rejected: it moves the failure into
the middle of a run, which is exactly where Principle IV's per-conversation isolation would swallow
it. Returning a result object from the loader instead of raising — rejected: nothing upstream has a
sensible second branch, and `load_settings` in #5 already establishes raising as this repository's
shape for configuration that is wrong.

## R7 — An unconfigured rule set warns; a configured one that is missing fails

**Decision** (the user's answer to Question 2): the setting `HERMES_PROJECT_RULES_PATH` defaults to
`data/projects.toml`, resolved against the repository root exactly as `archive_root` and
`import_state_path` are in #5. If the setting was not given and nothing is at the default location,
the classifier is built with an empty rule set, and one `warning` record is emitted naming the path
that was looked at, the fact that every conversation in this run will be `project:unknown`, and that
§17 will not revisit them. If the setting *was* given and nothing is there, loading fails.

**Rationale**: "did not configure" and "configured wrongly" are different mistakes and deserve
different answers. A first run — a dry run (#22), an experiment against a scratch bank — should not
require writing a rules file to get started; a run pointed at a path should never quietly proceed
without it.

The warning carries the consequence because the consequence is not obvious and is not reversible by
re-running: §17 skips an unchanged conversation, so tags written by a rule-less run stay as they
are until something reclassifies them, and nothing in this feature does. FR-012b makes saying so
part of the requirement rather than part of the documentation, because the person who needs to know
is reading the run's output, not the docs.

The default lives under `data/` on purpose: `.gitignore` already excludes it, so the one file in
this design that holds a person's own project names, repository names and local paths cannot be
committed to a public repository by accident. A `projects.example.toml` at the repository root
documents the format, mirroring `.env.example` and the test that keeps it honest.

**Alternatives considered**: refusing to run without a rule set (Question 2's option B) — rejected
by the user, and it would block the dry run of #22 behind configuration that run exists to avoid.
Silently accepting an empty rule set (option C) — rejected: it is the quiet failure this repository
consistently refuses. Defaulting to `config/projects.toml` — rejected: `config/` is tracked, so the
default location would be one `git add .` away from publishing a person's project list.

## R8 — The level-3 seam is a composition, demonstrated rather than described

**Decision**: FR-013's extension point is `ChainedProjectClassifier`, which holds an ordered
sequence of classifiers and returns the first resolved answer, falling through to `UNKNOWN_PROJECT`
when none resolves. The MVP composes exactly one element. The test composes two, the second being a
stub standing in for §15's level 3.

**Rationale**: §15 names three levels and forbids the third (§21). An extension point written as a
comment is not one; a chain with a second element exercised in a test is. It also pre-dates the
level that will actually arrive first in practice — level 1, explicit metadata — which Claude Code
and Codex sessions carry (#27, #28) and which will want the same composition with the
metadata-based classifier *ahead* of the alias rules.

Chaining is what satisfies §15's ordering without any element knowing about the others, so the
alias classifier stays a thing that answers from rules and nothing else.

**Alternatives considered**: a `fallback` parameter on the alias classifier — rejected: it makes one
implementation the owner of the ordering, and two more levels would nest it. A registry or plugin
hook — rejected: a sequence of three is not a plugin system, and §21 means nothing is loading
anything dynamically. Returning `None` from a classifier to mean "I cannot say" — rejected: it
re-introduces the second spelling of "unknown" that #9 deliberately refused; the chain tests the
tag against `UNKNOWN_PROJECT` instead.

## R9 — Where the code lives

**Decision**:

```text
src/hermes_memory/classification/
├── __init__.py          # public surface
├── classifier.py        # #9's protocol and UNKNOWN_PROJECT — UNCHANGED
├── rules.py             # ProjectRule and ProjectRuleSet: the validated vocabulary (FR-010)
├── loader.py            # path resolution, tomllib, error translation, the warning (R1, R6, R7)
├── matcher.py           # the compiled alternation and one scan (R2, R3, R4)
├── alias_classifier.py  # AliasProjectClassifier: match, then resolve by priority (R5)
└── chain.py             # ChainedProjectClassifier: the §15 seam (R8)
```

**Rationale**: the constitution's module tree fixes `classification`; this feature fills it. The
split follows what is separately testable — whether a string matches (`matcher`), whether a rule
set is well-formed (`rules`), whether a file becomes one (`loader`), and whether matches become a
tag (`alias_classifier`) — and leaves #9's declaration in `classifier.py` untouched, so the boundary
stays readable as a boundary rather than as the first implementation of one. It is the same shape
#11 used for `sanitization`, for the same reason.

**Alternatives considered**: one module — rejected: the matching rules and the resolution rules fail
differently and deserve to fail separately in the test output. Putting the loader in `settings.py` —
rejected: #5's settings answer "where is it", and this feature's loader answers "what is in it";
merging them would put a file format into the module every other feature imports.

## R10 — What is scanned, and what classification is not allowed to do

**Decision**: the matcher reads the same text-bearing fields #11's rewriter visits —
`Conversation.title`, each `Message.text`, each `ToolActivity.name`, `.request` and `.result`, each
`NonTextPart.name` — enumerated by name, with a structure test that fails when the model gains a
text field the matcher does not consider.

**Rationale**: FR-005 fixes the list, and #11 already established both the list and the guard test
for exactly this failure mode — a field added later that one stage silently stops covering. Using
the same enumeration keeps the two stages from drifting apart; a project named in a tool result that
the sanitizer scans and the classifier does not would be a difference nobody intended.

Identity fields are not scanned, and here that is free rather than a trade: `source_id` is an opaque
token and an alias matching it would be a coincidence, not evidence.

**Alternatives considered**: title only — rejected: the issue says title *and* content, and the
title of a ChatGPT conversation is frequently autogenerated and about the question rather than the
project. A recursive walk over all strings — rejected for the same reason #11 rejected it, plus it
would scan `source_id`.

## R11 — The classifier is silent; the loader is not

**Decision**: `classify` emits no log record. The loader emits at most two: the FR-012a warning when
no rule set was found at the default location, and one `info` record at load naming how many
projects and aliases were loaded, from which path. Neither carries conversation content.

**Rationale**: a per-conversation log line from classification would be one record per conversation
over a corpus of tens of thousands, and #19 already reports the run's outcome per conversation. The
project a conversation resolved to is part of what #19 reports, not a second stream. The load-time
records are the opposite case: they happen once and they are what distinguishes the three states a
person needs to tell apart — rules loaded, no rules found, rules refused.

**Alternatives considered**: a debug record per classification — rejected above, and it would tempt
a maintainer to include the matched alias, which is conversation content. Complete silence from the
loader too — rejected: FR-012a requires the warning, and a run that classified nothing must say why.

## R12 — Fixtures are synthesized, and the rule set in tests is a fixture too

**Decision**: every conversation and every rule set in the suite is synthesized, through the
existing `tests/synthetic/` helpers and `tests/contracts/conversations.py`. No real project list and
no real conversation enters the repository.

**Rationale**: CLAUDE.md forbids conversation content in the repository, and a real rule set is a
list of someone's repositories and local paths — not a credential, but not something a public
repository should carry either. Synthesized projects prove the rules exactly as well.

**Alternatives considered**: using this repository's own name as a test alias — harmless in itself,
and rejected only because a fixture that happens to be real invites the next one that is.
