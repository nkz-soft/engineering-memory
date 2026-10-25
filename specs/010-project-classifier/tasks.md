# Tasks: Project classifier

**Input**: Design documents from `/specs/010-project-classifier/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/rule-set.md](./contracts/rule-set.md)

**Tests**: Required. Principle III is non-negotiable, and the contract suite of #9 already exists
and must pass unchanged. Every task that adds behaviour is preceded by a task that writes its test.
That test must be run and **observed failing** before the implementation task starts.

**Organization**: by user story, in the priority order of [spec.md](./spec.md). Two things are
foundational because every story stands on them: the rule-set vocabulary, which every story
constructs, and the matcher, which is the mechanism every story's behaviour is observed through.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: US1–US6 from [spec.md](./spec.md)

## Path Conventions

Single project: `src/engineering_memory/classification/`, `tests/` at repository root, per
[plan.md](./plan.md#source-code-repository-root).

**Every conversation and every rule set in the suite is synthesized** (research R12). CLAUDE.md
forbids conversation content in this repository, and a real rule set is a list of someone's
repositories and local paths.

Each implementation task extends `src/engineering_memory/classification/__init__.py` with what it makes
public; T030 is what asserts the finished surface. `classifier.py` is **not edited by any task** —
it is #9's declaration, and this feature implements it rather than amending it.

---

## Phase 1: Setup

**Purpose**: the static guards, before anything is written into the module.

- [X] T001 [P] Write `tests/structure/test_classification_imports.py`: every `.py` under
      `src/engineering_memory/classification/` imports only the standard library, `pydantic`,
      `structlog`, `engineering_memory.errors`, `engineering_memory.normalization`,
      `engineering_memory.observability` and `engineering_memory.classification.*`. Nothing on
      `FORBIDDEN_AT_RUNTIME` of `tests/structure/test_boundary_interfaces.py` is allowed; reuse that
      list by import rather than copying it. Include a "still bites" test against a `tmp_path`
      package holding `import httpx`, so the guard is proved able to fail (Principle IV)
- [X] T002 [P] Write `tests/synthetic/projects.py`: helpers that build a `ProjectRuleSet` and a
      TOML document from synthesized project names and aliases, plus the near-miss pairs AM-2
      needs (`nz`/`nzxt`, `engineering-memory`/`engineering-memory-ui`). No real repository name, no real
      path, no real conversation (research R12)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the validated rule-set vocabulary and the matcher. No story can be observed until a
rule set can be built and a string can be asked which projects it names.

**⚠️ CRITICAL**: no user story work begins until this phase is complete.

- [X] T003 Write `tests/unit/test_project_rules.py` first and observe it fail: a well-formed rule
      set builds; a `project` that is not a valid §6 slug is refused naming it (RS-6); the slug
      `unknown` is refused (RS-7); a project declared twice is refused naming it (RS-8); an alias
      that is empty or holds no letter and no digit is refused naming it and its project (RS-9);
      one alias declared by two projects is refused naming the alias and both projects, compared
      case-insensitively so that `engineering-memory` and `engineering-memory` collide (RS-10); a `priority`
      that is not an integer is refused (RS-5); an unknown key at either level is refused naming
      the key (RS-5); an **empty** rule set is valid and refused by nothing (RS-11); every refusal
      is a `ProjectRulesError` and `issubclass(ProjectRulesError, BoundaryError)` is **False**
      (RS-12)
- [X] T004 Implement `src/engineering_memory/classification/rules.py`: frozen `ProjectRule` with
      `project: Slug`, `aliases: tuple[str, ...]` (at least one, each containing a letter or a
      digit) and `priority: int = 0`; frozen `ProjectRuleSet` with `rules: tuple[ProjectRule, ...]`
      carrying the cross-rule refusals; `ProjectRulesError(RuntimeError)`. `extra="forbid"` on both
      models, per the `FrozenModel` base of #8
- [X] T005 Write `tests/unit/test_alias_matcher.py` first and observe it fail — the mechanism, not
      yet the stories: a matcher built from a rule set reports which projects a string names;
      matching is case-insensitive by case folding, including a non-ASCII alias (AM-1); an alias is
      a literal, so `a.b` does not match `axb` and `(` in an alias is not metasyntax (AM-5); where
      two aliases could match at one position the longer wins and the match is attributed to its
      project (AM-6); a run of whitespace in an alias matches any non-empty run of whitespace
      including a line break (AM-4); the count of occurrences is not reported and repeating an
      alias changes nothing (AM-10); a matcher built from an empty rule set reports nothing for any
      string
- [X] T006 Implement `src/engineering_memory/classification/matcher.py`: compile every alias of every
      rule into one alternation, longest alias first, with the per-edge boundary of AM-2 and AM-3
      and the whitespace rule of AM-4; keep the map from casefolded alias to project; expose one
      method that scans a string once and returns the set of projects named (research R4)

**Checkpoint**: a rule set can be built and refused, and a string can be asked which projects it
names.

---

## Phase 3: User Story 1 - Conversations about a known project are found under that project (Priority: P1) 🎯 MVP

**Goal**: a conversation naming a configured project is classified under it, wherever in the
conversation the name appears.

**Independent Test**: configure one project with several aliases, classify conversations that
mention an alias in each of the six text-bearing fields, and assert all come back as that
project's tag.

- [X] T007 [P] [US1] Write `tests/structure/test_matcher_covers_the_model.py` first and observe it
      fail: enumerate the fields of #8's model and assert each text-bearing one is swept and each
      other one is not. Reuse the enumeration of `tests/structure/test_sanitizer_covers_the_model.py`
      rather than copying it, so the two stages cannot drift apart (research R10). Identity fields
      and timestamps are asserted **not** scanned (AM-8)
- [X] T008 [US1] Write `tests/unit/test_alias_matching.py` first and observe it fail: an alias
      found in `Conversation.title`, in a `Message.text`, in a `ToolActivity.name`, in its
      `.request`, in its `.result` and in a `NonTextPart.name` each yields that project's tag — six
      placements, six hits (SC-001); a different case in the text still matches (AM-1); a
      multi-word alias split across a line break still matches (AM-4); and exactly one project
      matched yields its tag whatever its priority (AR-2)
- [X] T009 [US1] Implement `src/engineering_memory/classification/alias_classifier.py`:
      `AliasProjectClassifier`, built from a `ProjectRuleSet`, holding a matcher; `classify`
      gathers the six text-bearing fields, joins them with `\n`, asks the matcher, and returns the
      single matched project's `ProjectTag`. Resolution of several matches lands in T014; until
      then a conversation matching several is out of this task's scope and its test is T013's

**Checkpoint**: a conversation naming one configured project is classified under it.

---

## Phase 4: User Story 2 - A conversation about nothing recognizable is still imported (Priority: P1)

**Goal**: no match is an answer, not a failure.

**Independent Test**: classify a conversation matching no rule; assert `project:unknown`, that
nothing was raised, and that the conversation is unchanged.

- [X] T010 [P] [US2] Write `tests/contracts/test_alias_classifier_passes_the_contract.py` first
      and observe it fail: subclass `ProjectClassifierContract` from `tests/contracts/classifier.py`,
      with `make_classifier` returning an `AliasProjectClassifier` over a **non-empty** rule set
      whose aliases the suite's conversations do not contain — so PC-2 is meaningful rather than
      accidental. Do not edit the suite (SC-007)
- [X] T011 [US2] Write the no-match cases into `tests/unit/test_project_resolution.py` first and
      observe them fail: no project matched yields `UNKNOWN_PROJECT` and `str(tag)` is
      `project:unknown` (AR-1); a classifier over an empty rule set yields it for every
      conversation; a conversation with no title and no messages yields it (AM-9); none of these
      raises (AR-8)
- [X] T012 [US2] Extend `alias_classifier.py` so that no match returns `UNKNOWN_PROJECT` rather
      than `None` or an exception, and confirm PC-1 to PC-5 now pass

**Checkpoint**: every conversation gets a tag, and the unresolved case is an ordinary one.

---

## Phase 5: User Story 3 - A conversation about two projects resolves the same way every time (Priority: P1)

**Goal**: ambiguity resolves by declared priority; a tie at the top resolves to `project:unknown`.

**Independent Test**: two projects at different priorities — the higher wins; level the
priorities — `project:unknown`; repeat and reorder — unchanged.

- [X] T013 [US3] Extend `tests/unit/test_project_resolution.py` first and observe the new cases
      fail: two matching projects at different priorities yield the higher (AR-3); two sharing the
      highest yield `UNKNOWN_PROJECT` (AR-4); three matching with two tied at the top yield
      `UNKNOWN_PROJECT`; a rule set in which no rule declares a priority makes any two-project
      conversation `UNKNOWN_PROJECT`, because the documented default gives them all `0`; two
      aliases of the **same** project are not ambiguity and yield that project (AR-5)
- [X] T014 [US3] Implement the resolution in `alias_classifier.py`: several matches resolve to the
      highest `priority`, or to `UNKNOWN_PROJECT` when the highest is shared (research R5)
- [X] T015 [US3] Extend `tests/unit/test_project_resolution.py` with the determinism cases and
      observe them fail: a hundred repeated classifications of one conversation agree; the same
      rules written in a different order give the same answer; two separately constructed
      classifiers over equal rule sets agree (AR-6, SC-003). Fix whatever ordering dependence they
      expose

**Checkpoint**: the ambiguous case is decided by the rule set, identically on every run.

---

## Phase 6: User Story 4 - The rules are the user's, and a broken rule set says so (Priority: P2)

**Goal**: the rule set comes from a file the user controls; loading it fails loudly when it is
wrong and warns loudly when it is absent — while `classify` keeps raising nothing.

**Independent Test**: load a broken rule set and get a message naming the offending entry; load
nothing from the default location and get a warning and an empty rule set; load a path that was
asked for and is missing and get a failure.

- [X] T016 [P] [US4] Write `tests/unit/test_settings_project_rules.py` first and observe it fail:
      `Settings` exposes `project_rules_path` defaulting to `data/projects.toml`, a relative value
      resolves against the repository root and an absolute one is left alone (#5's FR-013), and the
      settings object can say whether the field was explicitly set
- [X] T017 [US4] Implement `project_rules_path: Path = Path("data/projects.toml")` in
      `src/engineering_memory/settings.py`, reusing the existing path-resolution validator, and add
      `ENGINEERING_MEMORY_PROJECT_RULES_PATH` to `.env.example` under Local storage with a comment saying what
      it holds and that the default sits under the ignored `data/`. The sync test of #5 fails if
      one is added without the other
- [X] T018 [US4] Write `tests/unit/test_project_rules_loading.py` first and observe it fail: a
      valid TOML document loads into the expected rule set (RS-1); a path given explicitly with
      nothing at it raises naming that path (RS-2); no path given and nothing at the default
      location returns an **empty** rule set, raises nothing, and emits exactly one `warning`
      record naming the path, stating that this run classifies everything as `project:unknown`, and
      stating that re-importing will not revisit those conversations (RS-3, FR-012a, FR-012b); a
      file that is not valid TOML raises naming the file and the parser's complaint (RS-4); a file
      valid as TOML but not as a rule set raises naming the offending entry (RS-5); a file holding
      no project loads as an empty rule set **without** a warning (RS-11); loading emits one `info`
      record naming the path, the project count and the alias count (RS-13); no record carries
      conversation content. Capture records with the structlog harness #6 left in
      `tests/unit/conftest.py`
- [X] T019 [US4] Implement `src/engineering_memory/classification/loader.py`: resolve the path from
      `Settings` or an explicit argument, read it with `tomllib`, validate into a `ProjectRuleSet`,
      translate every failure into `ProjectRulesError` naming the file and the entry, and emit the
      two records of RS-13 and RS-3. The absent-default case is distinguished by whether the
      setting was explicitly set, not by comparing the value to the default (data-model.md)
- [X] T020 [P] [US4] Write `projects.example.toml` at the repository root in the shape
      [contracts/rule-set.md](./contracts/rule-set.md#the-configuration-file) fixes — two
      `[[project]]` entries, one with `priority` and one without, with comments explaining aliases
      and priority and ties — using invented project names only. Add a case to
      `tests/unit/test_project_rules_loading.py` that parses and validates the shipped example, so
      it cannot rot

**Checkpoint**: the rule set is the user's, a broken one stops the run, an absent one announces
itself.

---

## Phase 7: User Story 5 - Ordinary words do not become project names (Priority: P2)

**Goal**: a short alias does not claim every longer word containing it.

**Independent Test**: a configured alias matches when it stands as a term and misses when it is
embedded in a longer one.

- [X] T021 [US5] Write `tests/unit/test_alias_boundaries.py` first and observe it fail, as one
      table of hits and misses so the rule is pinned by examples: `nz` misses `nzxt` and hits
      `nz/engineering-memory`, `the nz repo`, `(nz)` and a line ending in `nz` (AM-2); `engineering-memory`
      misses `engineering-memory-ui` and `my-engineering-memory` and hits `nkz-soft/engineering-memory`,
      `D:/Projects/nz/engineering-memory` and `engineering-memory.md` (AM-2); an alias whose own edge is not
      a word character, such as `nkz-soft/`, imposes no constraint on that side and hits
      `nkz-soft/anything` (AM-3); and no alias matches across the `\n` join between two fields —
      a title ending `herm` beside a message beginning `es-memory` is a miss (AM-7)
- [X] T022 [US5] Fix whatever T021 exposes in `matcher.py`. If T006 already satisfies the table,
      record that in the task's commit message rather than inventing a change — a test that passes
      first time is evidence, not a failure of the process, provided it was written first and seen
      to fail against the absent behaviour

**Checkpoint**: the near-miss table is green, and SC-005 is asserted rather than assumed.

---

## Phase 8: User Story 6 - The seam for model-based classification is visible and unused (Priority: P3)

**Goal**: §15's third level attaches by composition, demonstrated by a test, and is absent from the
MVP.

**Independent Test**: compose the alias classifier with a stand-in for level 3 and assert the
stand-in is consulted only where the first resolved nothing.

- [X] T023 [P] [US6] Write `tests/unit/test_classifier_chain.py` first and observe it fail: a chain
      returns the first answer that is not `UNKNOWN_PROJECT` (CH-1); an element after that answer
      is **not** consulted, asserted by a stand-in that records whether it was called (CH-2); a
      chain whose elements all resolve nothing returns `UNKNOWN_PROJECT` (CH-3); an empty chain
      returns `UNKNOWN_PROJECT` (CH-4); and a chain is itself a `ProjectClassifier` passing PC-1 to
      PC-5 (CH-5)
- [X] T024 [US6] Implement `src/engineering_memory/classification/chain.py`:
      `ChainedProjectClassifier` over an ordered sequence of `ProjectClassifier`, returning the
      first resolved answer and `UNKNOWN_PROJECT` otherwise (research R8)
- [X] T025 [P] [US6] Add a case to `tests/structure/test_classification_imports.py` asserting no
      module in `classification` imports an HTTP client or a model SDK, so CH-6 — no model-based
      classifier in the MVP — is enforced statically rather than remembered (§21)

**Checkpoint**: the seam exists, is exercised, and is empty.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T026 [P] Write `tests/unit/test_classification_is_pure.py` and observe it fail where it must:
      `classify` performs no file read, no socket call and no clock read — **blocked** by
      monkeypatching the relevant entry points to raise, so the test passes because the call could
      not happen rather than because nobody looked (SC-008, AR-7); the conversation handed in is
      unchanged (PC-4); and `classify` emits no log record at all (AR-9, research R11)
- [X] T027 [P] Add a cost case to `tests/unit/test_alias_matcher.py`: a conversation carrying
      hundreds of kilobytes of text against a rule set of many projects classifies within a bounded
      time, and the bound does not change materially when the project count doubles — cost is
      bounded by the text, not by the rule count (research R4, plan Performance Goals)
- [X] T028 Update `src/engineering_memory/classification/__init__.py`: export `AliasProjectClassifier`,
      `ChainedProjectClassifier`, `ProjectRule`, `ProjectRuleSet`, `ProjectRulesError` and the
      loader entry point beside #9's `ProjectClassifier` and `UNKNOWN_PROJECT`, and rewrite the
      module docstring — it currently ends "The alias rules that decide the rest arrive with #12",
      which this feature makes untrue
- [X] T029 [P] Add the `project:` row to the quickstart of #5 or to `README.md` only if one already
      documents configuration files; otherwise skip this task and say so in the pull request rather
      than inventing a documentation surface this feature does not have
- [X] T030 Assert the public surface in `tests/structure/test_module_layout.py` (extend it): the
      names T028 exports are importable from `engineering_memory.classification`, and `classifier.py` is
      unchanged against `origin/main`
- [X] T031 Run [quickstart.md](./quickstart.md) end to end — every numbered section, including the
      two one-liners that show the warning and the failure apart — and reconcile any expectation it
      states with what actually happens
- [X] T032 Run `uv run pytest`, `uv run ruff check .` and `uv run ruff format --check .`, and quote
      the output in the pull request's verification section (superpowers:verification-before-completion)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup — **blocks every user story**
- **US1 (Phase 3)**: depends on Foundational
- **US2 (Phase 4)**: depends on US1 — it extends the same classifier
- **US3 (Phase 5)**: depends on US2 — resolution is the branch that sits beside no-match
- **US4 (Phase 6)**: depends on Foundational only; can run in parallel with US1–US3
- **US5 (Phase 7)**: depends on Foundational only; can run in parallel with US1–US4
- **US6 (Phase 8)**: depends on US2 — the chain's test needs a classifier that can resolve nothing
- **Polish (Phase 9)**: depends on everything above

### Within each story

Tests are written and **observed failing** before the implementation task starts. Rule-set
vocabulary before matcher; matcher before classifier; classifier before chain; loader independent
of all three.

### Parallel opportunities

- T001 and T002 together
- T016 and T020 together, and the whole of US4 alongside US1–US3
- US5's table (T021) alongside US1–US4
- T026, T027 and T029 together

---

## Implementation Strategy

### MVP

Phases 1–4. At that point a conversation naming a configured project is classified under it, every
other conversation is `project:unknown`, and #9's contract suite passes — which is the boundary
#19 needs. Priorities, the user's file and the chain are what make it usable rather than what make
it work.

### Incremental delivery

1. Setup + Foundational → a rule set can be built and a string matched
2. US1 + US2 → the boundary is implemented and the contract passes **(MVP)**
3. US3 → ambiguity is decided rather than accidental
4. US4 → the rules become the user's
5. US5 → the near-miss table is asserted
6. US6 → §15's third level has somewhere to attach

### Notes

- Commit after each task or logical pair, with the test commit observable before its implementation
- `src/engineering_memory/classification/classifier.py` is not edited by any task
- No fixture contains a real credential, a real conversation or a real project list

---

## What was done differently, and why

Four tasks did not land exactly as written. Each is a change of placement, not of scope.

- **T025** was already satisfied by **T001**. The import guard was written with a `MODEL_CLIENTS`
  list from the start, because the reason to forbid an HTTP client (Principle IV) and the reason to
  forbid a model SDK (§21, CH-6) produce the same check and a second test would have duplicated it.
- **T030** asserts the public surface and the untouched boundary in
  `tests/structure/test_classification_imports.py` rather than in `test_module_layout.py`, whose
  subject is the constitution's module tree rather than one package's exports. The "unchanged
  against `origin/main`" half is asserted as the *shape* of `classifier.py` — its public names —
  rather than as a diff: a test that shells out to git fails inside the container image of #7,
  where there is no repository.
- **T029** was performed rather than skipped. `README.md` already had a Configuration section, so
  the project rules are documented there, with the `projects.example.toml` pointer and the
  asymmetry between a configured and a default path.
- **T031** found three expectations in `quickstart.md` that did not match what the code does: the
  two `load_project_rules` one-liners used a signature invented before the loader existed, section
  3 described the boundary table with real project names where the fixtures use invented ones
  (research R12), and section 8 claimed the clock was blocked where it is in fact asserted
  statically. All three are corrected in `quickstart.md`, and the reason the clock is asserted
  differently is in the test's own docstring.

One test written earlier had to change when a later rule arrived: a tool activity named
`orchard-pipeline-deploy` was a hit in **T008** and is a miss under **T021**'s boundary rule. The
boundary rule is the more specific requirement, so the fixture moved to `orchard-pipeline/deploy`
and the former case is now asserted as a miss.

---

## Review findings, and what was done about them

A code review of the finished branch found three substantive defects. Each was reproduced before
being fixed, and each fix was mutation-checked where a test was involved.

- **AM-7 was broken, and its test passed vacuously.** The sweep joined fields with `\n` while AM-4
  relaxes the whitespace inside a multi-word alias — and `\s+` consumes a newline. With the alias
  `engineering memory`, a title ending "we discussed engineering" beside a message beginning
  "memory layouts" forged a match present in neither field, reachable from the multi-word alias
  `projects.example.toml` ships. The old test split a *single-word* alias across a line break,
  which the literal rule already refuses, so it would have passed with no join logic at all. The
  join is now `\x00` — a boundary character no whitespace class matches — the test uses a
  multi-word alias across a title and a message, and restoring the old join was confirmed to make
  it fail. `research.md` R4 stated the false premise outright and is corrected.
- **RS-10 and the matcher disagreed about what an alias is.** Validation compared `casefold()`
  while the matcher keyed on casefold plus whitespace normalization, so `foo bar` and `foo  bar`
  passed the duplicate check and then collided in the matcher, where the last declaration won and
  the other project's alias silently ceased to exist. Both now call one `alias_key`, and a test
  asserts they are literally the same function.
- **The documented performance property was not the one the code has.** `plan.md`, `research.md`
  and the spec's assumptions all claimed cost was independent of the rule count; `re` does not
  build a trie from a literal alternation, and the scan is linear in the alias count. The guard
  was toothless too — `large < small * 4` on a doubling passes for exactly linear growth, under a
  test named "does not double the scan". The claim is corrected everywhere to "one pass over the
  text rather than one per rule", the measurements are recorded in R4, and the test now measures
  the linearity instead of asserting it away.

Five smaller findings were also taken: SC-008 now states the loader suite as its exception, CH-6
is recorded as deferred to #19 with the static guard that stands in for it, `model_validate_json`
joins the two constructors that translate Pydantic's error, a hostile-alias and hostile-text table
exercises PC-5 where it is load-bearing, and the model-coverage test says in one line why AM-8's
derived `document_id` is outside its reach.

Two of the reviewer's observations were noted rather than acted on. Commits bundle tests with
their implementation, so test-first is visible in this document and in the session rather than in
the history — the repository's existing commits are feature-sized for the same reason. And nine
items the reviewer listed as out of scope are out of scope: pipeline wiring, level 1, and
model-based classification all belong to #19, #27, #28 and a decision §21 has not made.
