# Quickstart validation plan

These are implementation acceptance steps, not a record of checks already passed.

1. Have Python 3.13, uv, an installed Hermes with model access, and the existing local
   deployment/import environment working. Record versions. Use the #23 synthetic live
   fixture procedure; provision before import, never as part of server startup.
2. During implementation, run `uv sync --locked`, `uv run pytest`, `uv run ruff check .`
   and `uv run ruff format --check .`. Preserve red/green evidence per code change.
3. Run the new SDK stdio client integration against the installed entry point. Discover
   exactly search_memory and get_conversation. Test empty results, invalid arguments,
   safe dependency errors, distractor filtering, paging and original-secret exclusion.
4. Proposed Hermes recipe (replace paths; serve is introduced by this feature):

```yaml
mcp_servers:
  engineering-memory:
    command: /absolute/path/to/uv
    args: [run, --project, /absolute/path/to/engineering-memory, engineering-memory, serve]
```

Supply ENGINEERING_MEMORY_ settings through the launched process environment, including
absolute archive/state paths where used and the existing backend URL/token. Use the
same backend and bank as the importer. Credentials never go in committed YAML. Disable
any native Hindsight provider; this connection is the retrieval route. Confirm the
recipe against the actual installed Hermes version before publishing the operator guide.
Official configuration: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp

5. Start a fresh Hermes conversation; verify discovery. Ask explicitly to search memory
   for the imported synthetic decision without mentioning its answer. Require provenance
   and document_id, then request get_conversation and verify original context.
6. Repeat scoped to project/source with a second project's distractor, then retrieve a
   multi-page synthetic conversation and verify exact message order and page boundaries.
7. Repeat launch from an unrelated working directory and document prerequisites/errors.
8. Record date, commit, SDK/Hermes versions, exact commands, pass/fail outcomes and
   synthetic tool evidence in the operator documentation. Never copy private corpus or
   credentials. If live Hermes is unavailable, report that acceptance as unverified.
