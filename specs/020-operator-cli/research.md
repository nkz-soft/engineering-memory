# Research: Operator command line

## R1 — Reuse the existing CLI and composition boundaries

Decision: Extend `engineering_memory.cli` and retain `engineering-memory = engineering_memory.cli:main`.
Rationale: pyproject.toml already declares Typer and the installed entry point; cli/__init__.py already provides provision/version/help. Issue text predates those features.
Alternatives considered: replacing the CLI or adding FastAPI duplicates established behavior; HTTP was explicitly rejected in the issue.

## R2 — Distinguish run outcomes from durable status

Decision: Import displays RunReport including skipped; status enumerates latest imported/failed ImportRecords.
Rationale: ingestion/state.py explicitly rejects persistent skipped records because they would destroy skip eligibility. ImportState currently has only find/record, so status requires an enumeration extension with contract coverage.
Alternatives considered: storing skips or new run ledger adds incorrect semantics or unnecessary persistence scope.

## R3 — Existing pipeline owns policy

Decision: Compose IngestionPipeline with existing ChatGPT export/archive adapters and configured production adapters; map its semantic status to process codes.
Rationale: pipeline.py already owns archive ordering, failure isolation and force; report.py intentionally defers exit codes to CLI. RunReport properties require explicit JSON field construction.
Alternatives considered: reimplementing orchestration in callbacks creates competing skip/error behavior.

## R4 — Offline inspection and safe errors

Decision: Status loads only validated local state-path configuration and never initializes missing state. Render fixed categories and allowlisted stages rather than exception or persisted error strings.
Rationale: full Settings includes remote endpoints and must remain strict for operational writes; status needs neither remote service. Existing state error text is not a safe public output contract by itself.
Alternatives considered: full configuration/network requirement makes offline diagnosis impossible; weakening all settings validation would affect imports.

## R5 — Scope and dependencies

Decision: Respect ADR-006 force/resync, retain explicit provisioning, defer dry-run to #22.
Rationale: #17, #19 and #39 are closed; origin/main includes ingestion and bounded retry (#61). Architecture sections 21–22 allow the operator surface without a governance amendment.
Alternatives considered: auto-provision and automatic scheduling would change the agreed operator workflow.

No external API/library behavior is assumed beyond existing repository code. No unresolved technical unknown requires external research or a research agent.
