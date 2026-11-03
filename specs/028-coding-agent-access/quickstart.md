# Quickstart validation guide

Implementation and isolated client-registration checks are recorded in [verification.md](verification.md). Actual model-driven consumer acceptance remains blocked; follow the [operations guide](../../docs/operations/coding-agent-memory.md) to finish it.

## Prerequisites

- Python 3.13 and uv; installed Claude Code and Codex with usable model access.
- Prepared self-hosted backend, provisioned engineering-global bank, local archive and
  import settings. Follow docs/operations/hermes-memory.md for server prerequisites.
- Dedicated synthetic project with complete ChatGPT input and a second-project distractor.
- Credentials supplied privately via environment; snapshots staged only under ignored data/.

## Automated validation after implementation

```sh
uv sync --locked
uv run pytest tests/integration/test_coding_agent_access.py -q
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python deploy/hindsight/e2e.py
```

The regression file is implemented. The live gate must
include the new mandatory cross-source case; skips/missing cases are not passes.

## Live client journeys

1. Record `claude --version`, `codex --version`, `uv --version` and `git rev-parse HEAD`.
2. Dry-run/import the synthetic ChatGPT decision and competitor using existing CLI:

   ```sh
   uv run engineering-memory import --source chatgpt --export data/coding-agent-chatgpt --dry-run --json
   uv run engineering-memory import --source chatgpt --export data/coding-agent-chatgpt --json
   ```

3. Register each client using research.md and the operations guide linked above. Forward
   archive/backend/bank settings (and token if needed). Start clients outside the service
   checkout and confirm both read tools via `/mcp` and actual invocation.
4. Ask Claude Code to find the project's decision, without supplying its answer. Require
   search_memory with project/source filters and get_conversation for returned identity.
5. Discuss a unique synthetic refinement in Claude Code. Before import, have fresh Codex
   query it and record absence. Finish the Claude session and stage a quiescent snapshot.
6. Dry-run, then import using the existing supported source:

   ```sh
   uv run engineering-memory import --source claude-code --export data/coding-agent-claude-code --dry-run --json
   uv run engineering-memory import --source claude-code --export data/coding-agent-claude-code --json
   ```

7. Ask fresh Codex to retrieve the refinement with project/source filters, withholding its
   answer. Verify identity, original time, provenance and paged sanitized conversation.
8. Check disjoint project/source filters; repeat unchanged import and require skipped outcome.
9. Record safe commands, versions, tool calls/results and separate journey statuses in
   verification.md. An unsupported actual snapshot or missing client/service is an explicit
   blocker; never present synthesized fixtures as a real client conversation.

Expected outcomes follow contracts/consumer-validation.md. Use only synthetic evidence;
keep user settings, tokens and original snapshots out of commits and issue comments.
