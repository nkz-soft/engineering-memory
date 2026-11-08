# Feature Specification — Recall evaluation

**Feature Branch** `031-recall-evaluation`

**Created** 2026-11-07

**Status** Draft

**Input** [Issue #32](https://github.com/nkz-soft/engineering-memory/issues/32)

## User Scenarios & Testing

### User Story 1 — Score a fixed set of questions (P1)

As a memory maintainer, I can run the same questions against imported history and see which expected topics recall recovered.

**Why this priority**

A repeatable score gives the team a baseline for evaluating retention and retrieval changes.

**Independent test**

Run the benchmark against a controlled set of recall responses with known hits, misses, and partial matches.

1. Given a complete benchmark and an accessible corpus, when the maintainer runs it, every question contributes a topic coverage score and the report includes the aggregate and the seven category scores.
2. Given a successful lookup with zero results, the question scores zero. Given a failed lookup, the run fails and produces no completed report.
3. Given the same benchmark, scoring rules, and returned evidence, the question and aggregate scores are identical.

### User Story 2 — Measure the effect of a retain-mission change (P1)

As a memory maintainer, I can compare a baseline and changed retain mission using the same inputs, then inspect the category scores and retain the evidence of the experiment.

**Why this priority**

An aggregate alone can conceal a drop in one kind of retrieval.

**Independent test**

Import the same synthetic corpus into two isolated environments, changing only the retain mission, and run the same evaluation against each.

1. Given completed runs with matching benchmark, corpus, and retrieval settings, when the maintainer compares them, the overall and per-category changes are visible in percentage points.
2. Given a deliberately degraded extraction mission, the live experiment records a nonzero score difference and identifies where coverage changed.
3. Given results intended for the public repository, the committed reports contain scores, safe run identifiers, and topic coverage without private history, credentials, or recalled text.

### Edge Cases

- A missing question, duplicate identifier, malformed matcher, or missing category invalidates the benchmark before recall starts.
- Repeated memories and overlapping aliases count a topic at most once. Evidence from an unrelated conversation cannot satisfy a topic.
- A missing report, changed benchmark, different corpus, or different recall limit prevents a like-for-like comparison.

## Requirements

### Functional Requirements

- **FR-001** Maintain at least 30 unique questions across architecture decisions, technology choices, debugging investigations, root causes, failed approaches, infrastructure, and operational lessons. Each question has a stable ID, category, and one or more expected topics.
- **FR-002** Pair questions with a fixed, versioned synthetic engineering-history corpus. Every expected topic names acceptable wording and the source conversations that establish it.
- **FR-003** Run recall through the same read-only search surface consumers use, with a recorded fixed retrieval limit and benchmark project scope.
- **FR-004** Score each question as matched topics divided by expected topics. Average question scores equally overall and within each category. Preserve enough per-question counts and topic outcomes to explain both summaries.
- **FR-005** Produce a machine-readable report with benchmark, corpus, and scoring identifiers, retrieval settings, and safe run metadata. Reject invalid benchmark data and distinguish recall failures from valid misses. Completed reports cover the entire benchmark.
- **FR-006** Document a controlled experiment with fresh isolated memory and import state per run. Hold corpus, extractor, engine version, and retrieval settings fixed while changing the retain mission. Commit the baseline and changed reports and the measured difference.
- **FR-007** Restrict committed data and reports to synthetic benchmark material and allowlisted metadata. Exclude raw recall text, private archive data, local paths, endpoints, and credentials from reports and diagnostics.

### Key Entities

- **Benchmark** — versioned questions, expected topics, retrieval settings, and corpus identity.
- **Expected Topic** — stable ID, acceptable wording, and supporting conversation identities.
- **Run Report** — experiment identifiers, per-question outcomes, category scores, and overall score.

## Success Criteria

### Measurable Outcomes

- **SC-001** At least 30 valid questions cover all seven categories and yield exactly one outcome each in a complete run.
- **SC-002** For a fixed set of returned evidence, two evaluations produce identical per-question, category, and aggregate scores. A known partial match scores proportionally.
- **SC-003** Two committed reports from the controlled live mission experiment show a nonzero overall score difference and include every category, with reproduction instructions.
- **SC-004** Validation demonstrates that malformed data and interrupted lookups produce no completed report, and that published reports omit recalled text and secrets.

## Assumptions

- The published baseline uses authored synthetic conversations. The public score measures performance on that corpus.
- The first scoring rule uses curated wording variants with conversation-level provenance. It can miss valid paraphrases outside those variants.
- Use a retrieval limit of ten and a dedicated synthetic benchmark project tag for both runs. No pass/fail quality threshold is assumed.
- The live experiment requires an operator-controlled self-hosted deployment and a working extraction route. Issue #25 established the existing consumer path.
