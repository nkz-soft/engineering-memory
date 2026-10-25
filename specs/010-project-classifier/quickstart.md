# Quickstart: validating the project classifier

Everything here runs offline, on synthesized conversations and synthesized rule sets. No export, no
Hindsight instance and no real project list is needed — and per CLAUDE.md, no real conversation
content may be put in this repository to try it.

## Prerequisites

```bash
uv sync
```

## 1. The boundary contract passes, nothing skipped (SC-007)

```bash
uv run pytest tests/contracts/test_alias_classifier_passes_the_contract.py -v -rs
```

Expected: PC-1 to PC-5 pass with no skips, against a classifier built from a real rule set whose
aliases the suite's conversations do not contain. PC-2 is the one to read — it is what proves the
unresolved case is an answer rather than a failure.

## 2. A configured project is found wherever it is named (SC-001)

```bash
uv run pytest tests/unit/test_alias_matching.py -v
```

Expected: the alias is found in the title, in a message, in a tool activity's name, request and
result, and in a non-text part's name — six placements, six hits — plus the case-insensitivity and
multi-word cases of AM-1 and AM-4.

## 3. Short aliases do not eat longer words (SC-005)

```bash
uv run pytest tests/unit/test_alias_boundaries.py -v
```

Expected: the short alias `op` misses `option` and `op-code` and hits `the op repo` and
`op/service`; `orchard-pipeline` misses `orchard-pipeline-ui`, `my-orchard-pipeline` and `orchard`
alone, and hits `example-org/orchard-pipeline`, `orchard-pipeline.md` and `(orchard-pipeline)`; no
alias matches across the join between two fields (AM-7). The project names are invented, per
research R12 — a fixture that happens to be real invites the next one that is.

## 4. Ambiguity resolves by priority, and a tie does not resolve (SC-003)

```bash
uv run pytest tests/unit/test_project_resolution.py -v
```

Expected: the higher-priority project wins; the same conversation against levelled priorities comes
back `project:unknown`; a hundred repeated classifications agree; and the same rules written in a
different file order give the same answer.

## 5. A broken rule set is refused, an absent one is announced (SC-004, SC-004a)

```bash
uv run pytest tests/unit/test_project_rules_loading.py -v
```

Expected: RS-2, RS-4 and RS-5 each fail with a message naming the file and the offending entry,
and each raises `ProjectRulesError`. RS-3 is the opposite case: no failure, one warning, an empty
rule set. RS-11 is the third: an empty file is a choice, so it loads quietly.

The refusals that belong to the rule set rather than to the file — RS-6 to RS-10, and RS-12's
`not issubclass(ProjectRulesError, BoundaryError)` — are next door:

```bash
uv run pytest tests/unit/test_project_rules.py -v
```

See the difference yourself — the distinction FR-012a exists for:

```bash
uv run python -c "from pathlib import Path; from engineering_memory.classification import load_project_rules; load_project_rules(Path('data/projects.toml'), required=False)"
```

Expected: a JSON warning record on standard error naming `data/projects.toml`, stating that this
run will classify everything as `project:unknown`, and stating that a re-import skips an unchanged
conversation so those tags stay. Nothing raised, and an empty rule set returned.

```bash
uv run python -c "from pathlib import Path; from engineering_memory.classification import load_project_rules; load_project_rules(Path('nowhere.toml'), required=True)"
```

Expected: `ProjectRulesError` naming `nowhere.toml` and telling the reader they may unset the
setting to run without rules. The first command was not asking for a particular file; the second
was — `required` is the caller's statement of which, and `Settings.model_fields_set` is where it
comes from in the real composition.

## 6. Try it on a rule set of your own

```bash
cp projects.example.toml data/projects.toml
```

Edit it — your repositories, your paths, the shorthand you actually type — then:

```bash
uv run pytest tests/unit/test_project_rules_loading.py -k example -v
```

Expected: the shipped example parses and validates. `data/projects.toml` is ignored by git, so your
own list stays out of this public repository.

## 7. The level-3 seam is composed, and empty (SC-006)

```bash
uv run pytest tests/unit/test_classifier_chain.py -v
```

Expected: CH-1 to CH-5 — the fallback is consulted only where the alias classifier resolved
nothing, it is not consulted when it resolved something, and a chain is itself a classifier that
passes the boundary contract.

## 8. Nothing reached the network or the disk (SC-008)

```bash
uv run pytest tests/unit/test_classification_is_pure.py tests/structure/test_classification_imports.py -v
```

Expected: `classify` opens no file and no socket, with both blocked so that the test passes
because the call could not happen rather than because nobody looked; it emits no log record; and
the conversation handed in comes back unchanged. The clock is asserted differently and the
docstring says why — `from datetime import datetime` binds the class at import, so patching it
afterwards would not bite, and what is asserted instead is that the three modules which decide a
project import nothing that tells the time. The package also imports no Hindsight, no HTTP client,
no storage and no model SDK (Principle IV, §21).

## 9. The whole suite

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Expected: all green. The structure test that keeps `.env.example` and the settings object in step
(#5) is what fails if `ENGINEERING_MEMORY_PROJECT_RULES_PATH` was added to one and not the other.
