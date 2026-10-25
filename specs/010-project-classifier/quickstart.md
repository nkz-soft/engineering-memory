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

Expected: `nz` misses `nzxt` and hits `nz/hermes-memory` and `the nz repo`; `hermes-memory` misses
`hermes-memory-ui` and hits `nkz-soft/hermes-memory`; no alias matches across the join between two
fields (AM-7).

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

Expected: RS-2 and RS-4 to RS-10 each fail with a message naming the offending entry, and each
raises `ProjectRulesError` rather than a `BoundaryError` (RS-12). RS-3 is the opposite case: no
failure, one warning, an empty rule set.

See the difference yourself — the distinction FR-012a exists for:

```bash
uv run python -c "from hermes_memory.classification import load_project_rules; load_project_rules(path=None)"
```

Expected: a JSON warning record on standard error naming `data/projects.toml`, stating that this
run will classify everything as `project:unknown`, and stating that re-importing will not revisit
those conversations. Nothing raised.

```bash
uv run python -c "from hermes_memory.classification import load_project_rules; load_project_rules(path='nowhere.toml')"
```

Expected: `ProjectRulesError` naming `nowhere.toml`. The first command asked for nothing in
particular; the second asked for a file.

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

Expected: `classify` performs no file read, no socket call and no clock read — blocked, so that a
test passes because the call could not happen rather than because it was not noticed — and the
module imports no Hindsight, no HTTP client and no storage (Principle IV).

## 9. The whole suite

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Expected: all green. The structure test that keeps `.env.example` and the settings object in step
(#5) is what fails if `HERMES_PROJECT_RULES_PATH` was added to one and not the other.
