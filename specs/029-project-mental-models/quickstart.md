# Validation guide: Project mental models

Proposed Phase 2 sequence; new command/tool are not implemented or executed in planning.

## Prerequisites

Python 3.13/uv, isolated pinned self-hosted engine and configured test LLM, environment-only
credentials, isolated archive/state paths, provisioned test bank and supported synthetic exports.
Use existing deployment/provisioning guides. Never use personal history in public evidence.

## Validation sequence

1. `uv sync --frozen`, then `uv run engineering-memory provision --json` with isolated settings.
2. Prepare two complementary alpha conversations, beta competitor and untagged decoy. Use existing
   classification rules; keep expected facts outside model questions.
3. `uv run engineering-memory import --source chatgpt --export <synthetic-export> --json`.
   Confirm success and sanitized archive records.
4. `uv run engineering-memory models refresh --project alpha --json`. Expect three completed
   outcomes; repeat and confirm three logical identities, not three new definitions.
5. Connect a supported MCP client to `uv run engineering-memory serve`, discover get_project_model,
   call `{"project":"alpha","kind":"architecture"}`, then stack and decisions. Verify both
   expected alpha facts, no beta/untagged facts, refresh metadata and supports.
6. Open every support with get_conversation: exact document/provenance, original time, alpha scope,
   sanitized content. Check missing project, unsupported kind and blank inputs.
7. Import a later synthetic conversation explicitly superseding a stack choice; refresh. Next reads
   identify replacement plus historical rationale and supporting new conversation.
8. Exercise sparse/conflicting evidence, refresh failure/timeout, partial outcomes and repetition.
   Confirm last-good content/time survive and uncertain operations reconcile without duplicates.
9. Unchanged import and dry-run must not refresh models or re-extract unchanged conversations.

## Checks and evidence

Run targeted model/adapter/CLI/MCP cases, then `uv run pytest`, `uv run ruff check .`,
`uv run ruff format --check .`, extended isolated live model gate with no required-test skips.
Fixture LLM tests prove lifecycle; a real configured extractor run proves coherent synthesis.
Record actual engine/image/LLM versions, revision, safe commands, per-scenario outcomes and synthetic
support IDs in verification.md. Missing runtime/LLM is an acceptance blocker, not passing evidence.
