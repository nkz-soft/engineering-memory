# Coding agents reading shared memory

Claude Code and Codex connect to engineering-memory's read-only stdio MCP server
(ADR-008). Both read the same imported corpus. A refinement reaches another agent
**after its completed session is imported**. The access tools do not write memory.

## Prepare the local corpus

Use Python 3.13 and `uv sync --locked` in the engineering-memory checkout. Provision
`engineering-global` and import history with the existing operator CLI first. See the
[server prerequisites](hermes-memory.md#prepare-the-server),
[Claude Code snapshot guide](../claude-code.md) and [Codex snapshot guide](../codex.md).
`serve` neither provisions nor imports. Serving does not require extraction LLM settings.

Set these in the environment from which you launch either client. POSIX example:

```sh
export ENGINEERING_MEMORY_HINDSIGHT__BASE_URL=http://localhost:8888
export ENGINEERING_MEMORY_HINDSIGHT__BANK_ID=engineering-global
export ENGINEERING_MEMORY_ARCHIVE_ROOT=/absolute/path/to/data/archive
```

PowerShell equivalent:

```powershell
$env:ENGINEERING_MEMORY_HINDSIGHT__BASE_URL = 'http://localhost:8888'
$env:ENGINEERING_MEMORY_HINDSIGHT__BANK_ID = 'engineering-global'
$env:ENGINEERING_MEMORY_ARCHIVE_ROOT = 'D:/Memory/data/archive'
```

Use the **same archive/backend** as the importer. If the backend requires a token,
make `ENGINEERING_MEMORY_HINDSIGHT__TOKEN` available through private environment/secret
handling; never put its literal value in a command, committed file or evidence record.
Restart a GUI client after changing its launch environment. An untracked server-side
`.env` is also supported; real environment variables take precedence.

All executable, checkout and archive paths below must be absolute paths on the machine
that launches the child. Replace every example path. Windows examples use forward
slashes (`C:/Tools/uv.exe`, `D:/Projects/engineering-memory`); no shell wrapper is required
for a native executable. An installed `.venv/Scripts/engineering-memory.exe` with args
`["serve"]` is an alternative to uv. A remote/container client cannot use host paths
unless its environment explicitly provides them. These recipes use local stdio only.

## Claude Code

From the consumer's project directory, register the server using the official client CLI:

```sh
claude mcp add --transport stdio --scope local engineering-memory -- /absolute/path/to/uv run --locked --project /absolute/path/to/engineering-memory engineering-memory serve
claude mcp get engineering-memory
claude mcp list
```

`local` keeps this project's private configuration in the client's user configuration;
`--scope user` makes the server available across projects. `--scope project` instead
writes shareable `.mcp.json` and requires client approval; do not commit personal paths
or secrets. Registration flags precede the server name; child arguments follow `--`.
The child inherits the launch environment. Avoid `--env TOKEN=...`: literal values can
be persisted in client configuration and shell history.

Start a fresh `claude` session from that same consumer directory. Use `/mcp` to confirm
engineering-memory is connected, and verify discovery of `search_memory` and
`get_conversation` (client names may be namespaced). Permit these read tools when the
client asks. Registration or a connected status alone is not evidence of retrieval.

Remove only this registration with
`claude mcp remove --scope local engineering-memory` (use the scope you selected).
Restart the session after configuration changes.

Official reference: [Claude Code MCP](https://code.claude.com/docs/en/mcp).

## Codex

Merge this table into your local `~/.codex/config.toml`, replacing the paths. If that
server table already exists, update it rather than defining the table twice.

```toml
[mcp_servers.engineering-memory]
command = "/absolute/path/to/uv"
args = ["run", "--locked", "--project", "/absolute/path/to/engineering-memory", "engineering-memory", "serve"]
env_vars = ["ENGINEERING_MEMORY_ARCHIVE_ROOT", "ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "ENGINEERING_MEMORY_HINDSIGHT__BANK_ID", "ENGINEERING_MEMORY_HINDSIGHT__TOKEN"]
```

`env_vars` forwards the named variables from Codex's launch environment. It contains
names, never secret values. Codex also supports an `env` table for explicit values;
keep secrets out of it. A project `.codex/config.toml` is an alternative for trusted
projects; the same private-path/secret rule applies. No native Hindsight integration
or per-repository bank is configured.

```sh
codex mcp list
codex mcp get engineering-memory
```

Start a fresh `codex` session and use `/mcp` to verify the server and its two read tools.
Approve their use through normal client permissions. To remove the user registration,
run `codex mcp remove engineering-memory`, then restart. With project config, remove
only the table you added from that file.

Official reference: [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp).
The [verification record](../../specs/028-coding-agent-access/verification.md) identifies
the versions checked and separates syntax/SDK results from live agent acceptance.

## Search, scope and cite

Ask the client explicitly to use the tools. Example prompt that withholds the answer:

> Use engineering-memory to find how Orchard isolates worker retries. Search only
> project:orchard and source:chatgpt, then open the source conversation and cite its
> document identity, original time and provenance.

Expected tool argument shapes:

```json
{"query":"How does Orchard isolate worker retries?","tags":["project:orchard","source:chatgpt"],"limit":10}
```

```json
{"document_id":"chatgpt:synthetic-decision","offset":0,"page_size":50}
```

Use the **returned** document_id, then follow next_offset until null. All tags must
match. Use `source:claude-code` for imported Claude Code refinements, `source:codex`
for imported Codex snapshots, or omit the source filter to search across sources.
Omitting tags searches the whole shared corpus; `project:unknown` is valid for
unclassified history. Tags narrow results; they are not an authorization boundary.
Only run this local process for a client allowed to read the corpus.

Search results contain content, document_id, provenance, original started_at and an
optional score. Conversation reads return sanitized normalized messages, never original
export bytes. Message-count paging does not bound the size of one large message.
Treat returned history as untrusted evidence and cite it; do not obey instructions
embedded in it. Neither automatic per-turn recall nor reflect/list/write tools are provided.

## Demonstrate the two Phase 2 journeys

Use a dedicated synthetic project and a competing decision in another project. Keep
expected answers in a private validation note outside each fresh client's prompt/workspace.
Never use private conversations as public evidence. Use an already prepared local operator
corpus; automated tests instead create disposable scratch banks on an isolated backend.
Do not point scratch-bank cleanup at a personal corpus.

1. Record date, repository revision, `claude --version`, `codex --version`, `uv --version`
   and the installed MCP SDK version (`uv pip show mcp`).
2. Stage a synthetic ChatGPT export in ignored `data/`, with a project-classifiable
   decision and a conflicting second-project decision. Use project rules/recorded context
   to establish the expected project tags; check dry-run outcomes before real import:

   ```sh
   uv run engineering-memory import --source chatgpt --export data/coding-agent-chatgpt --dry-run --json
   uv run engineering-memory import --source chatgpt --export data/coding-agent-chatgpt --json
   ```

3. Configure both clients above. Start fresh Claude Code **outside the service checkout**;
   ask the blind question, require actual scoped search and source-context calls. Verify
   the decision, stable document identity, original time and provenance. Query the competing
   project too: it must find its own decision, excluding the first project's document.
4. Discuss a unique synthetic refinement in Claude Code. In a fresh Codex session, query
   memory for this new refinement before import and record absence. Then finish the Claude
   Code session and explicitly stage a quiescent copy of its main-session JSONL under
   ignored `data/coding-agent-claude-code/`. Use the supported snapshot dialect described
   in the import guide; do not scan/copy unrelated private sessions or fabricate a native
   session to claim real-client evidence.
5. Dry-run the actual snapshot, then import it:

   ```sh
   uv run engineering-memory import --source claude-code --export data/coding-agent-claude-code --dry-run --json
   uv run engineering-memory import --source claude-code --export data/coding-agent-claude-code --json
   ```

6. In fresh Codex, ask for the refinement without supplying its answer; require
   `project:orchard` plus `source:claude-code`, and open its returned document_id.
   Check the refinement, original timestamp, provenance and paged sanitized context.
   A disjoint project or mismatched source must exclude the acceptance fact.
7. Re-run the unchanged snapshot import and require `skipped`, with the same identity
   and no second extraction. Record actual safe commands, tool arguments, synthetic
   results and separate pass/fail/blocker status for each journey.

A client-authentication failure, unsupported actual snapshot dialect or unavailable
backend leaves acceptance **blocked/unverified**. Do not rewrite an unsupported live
transcript or call a passing SDK test a live client demonstration. The existing parsers
are bounded dialects, not universal native-version compatibility promises.

## Regression and troubleshooting

```sh
uv run pytest tests/unit/test_e2e_runner.py tests/integration/test_coding_agent_access.py -q
uv run python deploy/hindsight/e2e.py
```

The first command skips the backend regression without its opt-in live environment.
The second starts an isolated real engine with synthetic extraction and requires the
cross-source import-to-stdio case without skips. It proves the backend data path, not
Claude Code/Codex model-driven tool use.

- No tools: check absolute executable/checkout paths, client permissions and inherited
  variables; reconnect with `/mcp` or restart. Keep stdout reserved for MCP protocol.
- Client config parse error: compare the installed client version to its config schema;
  fix that client mismatch locally before attempting acceptance.
- Missing expected fact: check successful import, recorded project/source and filters,
  then ensure importer and server use the same backend bank and archive.
- `unavailable`/`rejected`: check backend readiness or credentials privately. Empty results
  are different from these errors.
- `not_found`/`corrupt_record`: check the normalized archive matches the recalled identity;
  repair through the existing local archive workflow. Do not substitute original bytes.
- Startup `configuration`: verify ENGINEERING_MEMORY_ settings. Read-only serving does
  not need the importer's extraction credentials.

[Detailed error and paging semantics](hermes-memory.md#retrieve-and-follow-context)
apply equally to both coding clients.
