# Feature Specification: Project classifier

**Feature Branch**: `010-project-classifier`

**Created**: 2026-10-25

**Status**: Draft

**Input**: Issue #12 — "Classify the project deterministically by alias rules"

## User Scenarios & Testing *(mandatory)*

There is one bank, `engineering-global`, and ADR-002 pays for that simplicity with a single
promise: that `project:` tags are good enough to narrow recall within it. Nothing in the pipeline
keeps that promise yet. Every conversation imported today would arrive carrying no project at all,
which is not a neutral state — it is the shared bank without the mechanism that makes a shared bank
workable.

§15 names three levels of project detection. Level 1, explicit metadata, needs a repository or a
working directory, and a ChatGPT export carries neither. Level 3, model-based classification, is
out of scope by §21 — and would be the wrong instrument anyway, because §17 requires a re-import to
be idempotent and a classifier that answers differently on the second run files the same
conversation under two projects. That leaves level 2: deterministic rules over names the user
already knows, which is what this feature builds.

Its users are the person importing a decade of their own history, who knows their projects by names
nobody else would guess; the person recalling a fact afterwards, who narrows by `project:` and needs
the narrowing to be trustworthy in both directions — what is there, and what is not; and #19, which
composes this stage and must not have to handle a failure from it.

Every story is testable with no export file, no network and no Hindsight instance in reach. The
input is a conversation in the normalized model of #8, and the rules are fixtures.

### User Story 1 - Conversations about a known project are found under that project (Priority: P1)

Someone who has worked on `engineering-memory` for a year calls it, across their history, by its
repository name, by the path they keep it at, and by the two shorthand names they actually type.
They configure those names once. From then on every conversation that mentions any of them is
retained under `project:engineering-memory`, and a recall narrowed to that project returns them.

**Why this priority**: It is the whole value of the feature and the only thing that makes the
shared bank of ADR-002 narrowable. Without it, `project:` is a tag with one value.

**Independent Test**: Configure one project with several aliases, classify conversations that
mention each alias in a different place — the title, a message, a tool result — and assert all of
them come back as that project's tag.

**Acceptance Scenarios**:

1. **Given** a rule set in which `engineering-memory` declares the aliases `engineering-memory`,
   `nkz-soft/engineering-memory` and `engineering memory`, **When** a conversation whose title contains
   `nkz-soft/engineering-memory` is classified, **Then** the result is `project:engineering-memory`.
2. **Given** the same rule set, **When** the alias appears in a message's text rather than the
   title, **Then** the result is the same.
3. **Given** the same rule set, **When** the alias appears in a tool activity's request or result,
   or in an attachment's name, **Then** the result is the same.
4. **Given** an alias written in a different case to the rule — `engineering-memory` against
   `engineering-memory` — **When** the conversation is classified, **Then** it still matches.

---

### User Story 2 - A conversation about nothing recognizable is still imported (Priority: P1)

Most of the corpus is not about a project. It is a question about Postgres isolation levels, a
rewritten paragraph, a recipe. §15 says plainly that a substantial share will not resolve, and
that those conversations are imported anyway, tagged `project:unknown`, and stay retrievable —
which is possible precisely because there is one shared bank.

**Why this priority**: It is the common case, not the error case, and the contract of #9 already
fixed it (PC-2, PC-5). A classifier that signalled "no project" by raising, or by returning
nothing, would turn the pipeline's failure path into its ordinary path.

**Independent Test**: Classify a conversation matching no rule and assert the result is
`project:unknown`, that nothing was raised, and that the conversation is unchanged.

**Acceptance Scenarios**:

1. **Given** any rule set, **When** a conversation matching no alias is classified, **Then** the
   result is `project:unknown`.
2. **Given** an empty rule set, **When** any conversation is classified, **Then** the result is
   `project:unknown` and no error is raised.
3. **Given** a conversation with no title and no messages, **When** it is classified, **Then** the
   result is `project:unknown`.

---

### User Story 3 - A conversation about two projects resolves the same way every time (Priority: P1)

Real history does not respect project boundaries. A conversation comparing two services mentions
both; a migration thread names the system being left and the one being moved to. Whatever the
answer is, it must be the same answer on the first run and on the re-import six months later, and
it must be the answer a person can predict from the rule set without reading the code.

**Why this priority**: §17 makes idempotency a requirement, not a quality: a conversation that
classifies one way today and another way tomorrow is retained twice under two projects, and the
duplicate is in a store built to replicate facts across a graph. The issue names the ambiguous case
as an acceptance criterion for exactly this reason.

The rule set settles it, and settles it visibly: each project declares a priority, the
highest-priority match wins, and where the top priority is shared the classifier declines to guess
and answers `project:unknown`. A tie is the rule set saying nothing, and the classifier says nothing
back rather than inventing a preference.

**Independent Test**: Configure two projects at different priorities, classify a conversation
matching both, assert the higher-priority project wins; then level the priorities and assert the
same conversation resolves to `project:unknown`.

**Acceptance Scenarios**:

1. **Given** a rule set in which two matching projects declare different priorities, **When** a
   conversation matching both is classified, **Then** the result is the higher-priority project.
2. **Given** a rule set in which two matching projects declare the same priority, **When** a
   conversation matching both is classified, **Then** the result is `project:unknown`.
3. **Given** the same conversation and rule set, **When** it is classified a hundred times, **Then**
   every result is identical.
4. **Given** the same rules written into the configuration in a different order, **When** the
   conversation is classified, **Then** the result is unchanged — priority is declared, not
   positional.
5. **Given** the same conversation, **When** it is classified by a separately constructed
   classifier over an equal rule set, **Then** the result is the same — the answer belongs to the
   rules, not to the process.
6. **Given** a rule set in which no project declares a priority, **When** a conversation matching
   two of them is classified, **Then** the result is `project:unknown`, because the documented
   default gives them all the same priority.

---

### User Story 4 - The rules are the user's, and a broken rule set says so (Priority: P2)

The aliases cannot be shipped in the repository: they are one person's project names, paths and
repositories, and the next person's are different. So they are configuration — and configuration
that is wrong must fail where failures are allowed to be loud. A misspelled project slug, a
duplicate alias claimed by two projects, a file that is not parseable: each of these is caught when
the rule set is loaded, with a message naming what is wrong, before a single conversation is
classified.

**Why this priority**: A quiet failure here is the expensive kind. A rule set that silently loaded
as empty would tag an entire import `project:unknown`, and the damage is only visible months later
when a recall returns nothing — by which time the bank is full. P2 rather than P1 because the
classification itself is what the issue asks for, and loading is how it is fed.

Not configuring the rules at all is a different thing from configuring them wrongly, and the two
must not be confused. A run that was pointed at a file finds that file or stops. A run that was
pointed at nothing starts with no rules — and says so loudly enough that nobody discovers it from a
recall that returns nothing six months later.

**Independent Test**: Load a rule set containing a duplicate alias, an invalid slug, and a
reference to a missing file, and assert each is refused at load time with a message naming the
offending entry — while `classify` itself still raises nothing for any conversation.

**Acceptance Scenarios**:

1. **Given** a configuration file that is not parseable, **When** the rule set is loaded, **Then**
   loading fails with a message naming the file and the problem.
2. **Given** a rule declaring a project slug that the tag convention of §6 does not permit, **When**
   the rule set is loaded, **Then** loading fails and names that rule.
3. **Given** two projects declaring the same alias, **When** the rule set is loaded, **Then**
   loading fails and names the alias and both projects — an alias that identifies two projects
   identifies neither.
4. **Given** a rule set location given explicitly and nothing at that location, **When** it is
   loaded, **Then** loading fails and names the path that was asked for.
5. **Given** no rule set configured and nothing at the default location, **When** the classifier is
   built, **Then** it is built with no rules, one prominent warning is emitted naming where it
   looked and what the run will therefore do, and classification proceeds.
6. **Given** a valid rule set, **When** any conversation is classified, **Then** no error is raised
   regardless of its content (PC-5).

---

### User Story 5 - Ordinary words do not become project names (Priority: P2)

Aliases are short, and short strings occur inside longer ones. A project called `api` would claim
every conversation containing `rapid`; a project called `nz` would claim `nzxt`. The failure is
silent in the direction that matters least — over-matching does not lose a conversation, it files it
under the wrong project, where it pollutes a recall that was narrowed in order to be trusted.

**Why this priority**: The issue names a unique-alias hit as an acceptance criterion, and a match
that is not unique is not a hit. P2 because a misfiled conversation degrades recall while a missed
one merely lands in `project:unknown`, which §15 already treats as acceptable.

**Independent Test**: Configure a short alias and assert it matches when it stands as a word and
does not match when it is embedded in a longer word.

**Acceptance Scenarios**:

1. **Given** the alias `nz`, **When** a conversation mentions `nzxt`, **Then** it does not match.
2. **Given** the alias `nz`, **When** a conversation mentions `nz/engineering-memory` or `the nz repo`,
   **Then** it matches.
3. **Given** the alias `engineering-memory`, **When** a conversation mentions `engineering-memory-ui`,
   **Then** it does not match that alias.
4. **Given** a multi-word alias such as `engineering memory`, **When** a conversation contains those
   words separated by a line break or by repeated spaces, **Then** it matches.

---

### User Story 6 - The seam for model-based classification is visible and unused (Priority: P3)

§15 ends with a level this feature is forbidden to build. What it can do is leave the place where
that level will attach — and leave it demonstrated, not described, so that adding level 3 later is a
composition rather than a rewrite of this one.

**Why this priority**: The issue asks for a documented extension point. P3 because nothing depends
on it yet, and it is cheap to leave now and expensive to carve out of an implementation written
without it.

**Independent Test**: Compose the alias classifier with a second classifier standing in for level 3,
and assert the second is consulted only for the conversations the first resolved as unknown.

**Acceptance Scenarios**:

1. **Given** the alias classifier composed with a fallback, **When** a conversation matches an
   alias, **Then** the fallback is not consulted.
2. **Given** the same composition, **When** a conversation matches no alias, **Then** the fallback
   decides, and its answer is the result.
3. **Given** a fallback that resolves nothing either, **When** a conversation is classified, **Then**
   the result is `project:unknown`.
4. **Given** the MVP's configuration, **When** the pipeline is assembled, **Then** no model-based
   classifier is present and no network call is made (§21).

---

### Edge Cases

- **An alias that is also an ordinary English word** — a project called `atlas` or `phoenix`. The
  word-boundary rule of Story 5 does not help; the rule set's author is who decides, and the
  documentation says so rather than the implementation guessing.
- **An alias appearing only inside a redacted region.** Classification runs after sanitization in
  §7, so what it reads is `[REDACTED]`. A project whose only evidence was a credential is not
  classifiable, and that is correct.
- **A rule whose project slug is `unknown`.** It would be indistinguishable from the no-match
  answer, so it is refused at load time rather than quietly collapsed.
- **An alias that is the empty string, or only punctuation.** It would match everything or nothing;
  refused at load time.
- **A conversation that matches two aliases of the same project.** One project, one answer — this is
  not ambiguity and must not be treated as such.
- **A conversation matching three projects, two of which share the top priority.** The third loses
  on priority and the remaining two tie, so the answer is `project:unknown`: a tie at the top is a
  tie whatever lost below it.
- **A rule set in which every project shares one priority**, which is what a user who never thought
  about priorities has. Unique matches are unaffected; only genuinely ambiguous conversations fall
  to `project:unknown`, which is the behaviour §15 already expects.
- **A very long conversation** — a dumped manifest, a pasted log of tens of thousands of lines.
  Classification is proportional to the text and does not degrade the run.
- **A conversation whose only evidence is in a non-text part's name**, such as an attached
  `engineering-memory-architecture.pdf`.
- **Unicode in aliases and in content** — a project named with non-ASCII characters, or content in
  which the alias is adjacent to a non-ASCII character. Case folding and boundaries behave for text
  that is not ASCII.
- **A conversation already classified in an earlier run**, re-imported from the archive: it
  classifies to the same project, because the rules and the content are the same (§17).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a project classifier satisfying the boundary declared in #9 —
  handed a normalized conversation, returning a `ProjectTag`, raising nothing.
- **FR-002**: Classification MUST be driven by a rule set supplied as configuration, in which each
  project declares a slug and the aliases that identify it. The rules MUST NOT be fixed in code:
  they are one user's project names, and the repository is public.
- **FR-003**: An alias MUST match case-insensitively.
- **FR-004**: An alias MUST match only where it stands as a whole term — bounded at both ends by
  something other than a letter or a digit — so that a short alias cannot be claimed by a longer
  word that contains it.
- **FR-005**: Matching MUST consider every field of the conversation that can carry text: the title,
  each message's text, each tool activity's name, request and result, and each non-text part's
  name.
- **FR-006**: A conversation matching no alias MUST be classified `project:unknown`, and MUST NOT be
  signalled by `None`, by an exception, or by any other means.
- **FR-007**: A conversation matching aliases of two or more projects MUST resolve to the matching
  project with the highest declared priority. Where the highest priority is shared by two or more
  matching projects, the result MUST be `project:unknown`: the rule set does not say which project
  wins, so neither does the classifier.
- **FR-007a**: Each project rule MUST carry a priority declared in the configuration, independent of
  the order the rules are written in, so that a reader of the rule set can predict every outcome
  from the rule set alone. A rule that declares no priority MUST take a documented default, and two
  projects sharing a priority MUST be permitted — that is what FR-007 resolves.
- **FR-008**: Classification MUST be deterministic and independent of the order rules are written
  in, of the iteration order of any collection, and of the order conversations are processed in: the
  same conversation and the same rules produce the same tag, across calls, instances and runs.
- **FR-009**: Classification MUST be pure — the conversation handed in is unchanged, no file is
  read, no network call is made, and no clock is consulted.
- **FR-010**: The rule set MUST be validated when it is loaded, and loading MUST fail with a message
  naming the offending entry when a project slug is not a valid `project:` value under §6, when an
  alias is empty or contains no letter or digit, when the slug `unknown` is declared, when one
  alias is declared by two projects, when a priority is not of the declared kind, or when one
  project is declared twice.
- **FR-011**: A configuration file that cannot be read or parsed MUST fail at load time with a
  message naming the file and the problem. No failure of loading may surface as a conversation
  silently classified `project:unknown`.
- **FR-012**: Where the rule set lives MUST be configurable through the environment, consistent with
  the settings of #5, and the shipped example configuration MUST document it. The setting MUST have
  a documented default location.
- **FR-012a**: A rule set explicitly configured and not readable MUST fail at load time (FR-011). A
  rule set left at its default location and not present MUST NOT fail: the classifier is built with
  no rules, every conversation resolves to `project:unknown`, and the run MUST emit one prominent
  warning saying that no rules were found, where it looked, and that this run will classify nothing.
  The two cases MUST be distinguishable — "did not configure" is not "configured wrongly".
- **FR-012b**: The warning of FR-012a MUST state that tags written by such a run do not correct
  themselves later: §17 skips an unchanged conversation on re-import, so a conversation retained as
  `project:unknown` stays that way until something reclassifies it, which this feature does not
  provide.
- **FR-013**: The feature MUST leave a documented extension point at which §15's level 3 attaches —
  demonstrated by composing the alias classifier with a second classifier consulted only where the
  first resolved nothing — and MUST NOT implement model-based classification (§21).
- **FR-014**: The classifier MUST NOT log conversation content, consistent with #6 and Principle V;
  what it may emit is the project it resolved and the conversation's source id.
- **FR-015**: The implementation MUST pass the contract suite of #9 (PC-1 to PC-5) unchanged, as any
  classifier must.
- **FR-016**: Classification MUST operate on one conversation at a time, so that one failure cannot
  abort a run (Principle IV, §18).

### Key Entities

- **Project rule**: one project — the slug that becomes its `project:` tag, the aliases that
  identify it (repository names, paths, project names and shorthand), and its priority, which is
  what decides a conversation that matches more than one project. It is the unit a user adds when
  they start a new project.
- **Priority**: a declared ordering over projects, used only to resolve a conversation matching
  several. Declared rather than positional so that moving a rule in the file cannot change how a
  conversation is filed, and shareable between projects so that "these two are equally plausible"
  is sayable — which is what produces `project:unknown` rather than a guess.
- **Rule set**: the validated collection of project rules a classifier is built from. Validation
  belongs to it rather than to classification, because this is where failing loudly is allowed.
- **Alias**: one literal term that identifies a project. Not a pattern: see the assumptions.
- **Classification outcome**: a `ProjectTag` — a resolved project or `project:unknown`. There is no
  third kind of answer, and `project:unknown` is an answer rather than the absence of one (§15).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A conversation mentioning a configured alias in any one of the title, a message, a
  tool activity's name, request or result, or a non-text part's name is classified under that
  project — six for six, none skipped.
- **SC-002**: A conversation matching no alias is classified `project:unknown`, and no classification
  of any conversation in the suite raises.
- **SC-003**: A conversation matching two projects at different priorities resolves to the higher
  one; the same conversation against equal priorities resolves to `project:unknown`; and both
  results hold on every one of a hundred repeated classifications and under every ordering of the
  rules in the file.
- **SC-004**: Every invalid rule set the suite offers — unparseable file, invalid slug, reserved
  slug, empty alias, alias claimed twice, a configured path with nothing at it — is refused at load
  time with a message naming what is wrong, and none of them is reachable by a classify call.
- **SC-004a**: An unconfigured rule set with nothing at the default location produces a built
  classifier, one warning naming the location and the consequence, and no failure — distinguishable
  in the run's output from the configured-and-missing case of SC-004.
- **SC-005**: Across a fixture of near-miss content — the alias embedded in a longer word, a longer
  word embedded in the alias — zero misclassifications are made.
- **SC-006**: Removing the fallback from the composed classifier changes the result only for
  conversations that resolved to `project:unknown`.
- **SC-007**: The implementation passes the contract suite of #9 without a change to the suite.
- **SC-008**: No classification test performs a network call or a filesystem write, blocked rather
  than merely unobserved. The loader's own suite is the stated exception: reading a file is what it
  does, so its tests write TOML into a temporary directory and the blocking applies to `classify`,
  where the property is load-bearing.

## Assumptions

- **Aliases are literal terms, not patterns.** No regular expressions, no globs. A pattern language
  in configuration is a second thing to specify, to validate and to defend against — catastrophic
  backtracking included — and the issue asks for names, paths and aliases, all of which are
  literals. A user who needs a pattern adds the two spellings.
- **A rule either matches or it does not; matches are not scored.** Counting occurrences would make
  the answer depend on how often a word happened to be repeated, which is an artifact of how someone
  typed, not evidence of what they were working on, and it would make the outcome sensitive to the
  parser.
- **Classification reads the conversation it is handed, which is the sanitized one.** §7 puts
  sanitize before classify, and this feature does not change that order.
- **The project of a conversation is single-valued.** §6 gives one `project:` namespace and the
  boundary of #9 returns one tag. Multi-project conversations are an ambiguity to resolve, not a set
  to emit; emitting several would be a change to the tag convention, which Governance puts behind a
  decision record.
- **An unresolved tag is not corrected retroactively.** §17 skips an unchanged conversation on
  re-import, so a conversation retained under `project:unknown` — because the rules were absent,
  incomplete, or genuinely ambiguous — keeps that tag until something reclassifies it. Nothing in
  this feature reclassifies anything; FR-012b only obliges the run to say so. A reclassification
  pass over the archive is separate work, and Principle I is what makes it possible later.
- **The rule set is configuration, not data under `data/`.** It holds no conversation content and no
  credential — project names, repository names and paths. It is a file the user writes and may keep
  outside the repository; nothing in this feature writes it.
- **The `type:` tag is not this feature's business.** §6 names a type vocabulary and §15 names
  project detection; they are separate, and the type is decided by whichever feature first needs to
  tell a troubleshooting thread from a decision.
- **Provenance is populated by the enrich stage, not here.** The classifier returns the tag; #19
  derives the provenance's project from it rather than classifying twice.
- **Fixtures are synthesized.** No real conversation and no real project list enters the repository,
  per CLAUDE.md.
- **The text is read once per conversation, not once per rule.** The corpus is large enough that
  re-reading every conversation for every project would be felt. Cost still grows with the number
  of aliases, which is acceptable at the scale a personal rule set reaches and is measured rather
  than assumed; the suite asserts the outcome, not the strategy, so an implementation that needs
  to index later may.

## Dependencies

- **#9 — boundary interfaces** (merged): declares `ProjectClassifier`, `UNKNOWN_PROJECT`, the
  contract suite PC-1 to PC-5, and the in-memory fake this feature replaces with the real thing.
- **#8 — normalized conversation model** (merged): the conversation being classified, the
  text-bearing fields FR-005 enumerates, and the `ProjectTag` with its slug validation.
- **#5 — environment configuration** (merged): how the rule set's location is configured and
  documented in `.env.example`.
- **Blocks #19 — the ingestion pipeline**, which composes this stage between sanitization and
  enrichment.
