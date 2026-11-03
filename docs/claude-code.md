# Importing Claude Code session snapshots

Save a quiescent copy of the main-session JSONL files under ignored `data/`. Select either one
file or a directory containing top-level session files:

```powershell
uv run engineering-memory import --source claude-code --export data/claude-code --dry-run --json
uv run engineering-memory import --source claude-code --export data/claude-code --json
uv run engineering-memory import --source claude-code --from-archive --force --json
```

Each file must contain one native session id, unique conversational record ids and timezone-bearing
source timestamps. Supported user/assistant records carry `sessionId`, `uuid`, `timestamp`, optional
`cwd` and `repository`, and `message.content` as text or ordered blocks. This is a bounded,
fixture-defined local transcript dialect, not a promise that every Claude Code version uses it.
See [the full dialect](../specs/026-claude-code-source/data-model.md) and ADR-010.

The adapter preserves command arguments, tool outputs, error flags and textual diffs, associates
results by native call id, and keeps their recorded order. An unfinished call has no invented
result. Unsupported blocks become markers; full original bytes remain in the local archive.
Nested subagent files and symlinks are excluded; recorded tools are never executed, and referenced
output or attachment paths are never read. Copy any required evidence into the selected snapshot
before import; missing external output cannot be reconstructed by this adapter.

Projects resolve from recorded repository context, then working directory, before prose aliases.
Configured aliases may map the context to an established project; otherwise its basename becomes
a lowercase slug. First usable context wins; later directory changes do not reassign the session.
No git checkout is consulted. Basenames can collide, so configure aliases for ambiguous projects.
A missing repository remains absent in provenance even when cwd resolves a project.

Documents use `claude-code:{sessionId}` with `source:claude-code` and the usual `project:` tag.
The common sanitizer covers context and tool payloads before retention or sanitized access.
Unchanged imports skip extraction; changed tool evidence updates the same document. Context-only
corrections follow existing metadata behavior: use `--force` to refresh them. Archive replay
reparses original bytes and does not depend on the original session directory.

Run the opt-in live root-cause recall test with an isolated contract stack ready:

```powershell
$env:ENGINEERING_MEMORY_LIVE_CONTRACT = '1'
uv run pytest tests/integration/test_claude_code_live.py -q
```

The extraction dependency is synthetic; the memory engine, retention, filtering, recall and
sanitized archive access are real. Unit/CLI tests alone do not establish live recall semantics.

## Reading shared memory from Claude Code

To retrieve imported history, follow the [coding-agent memory setup](operations/coding-agent-memory.md).
Reads use the local read-only MCP access surface. A refinement reaches another agent only after
this completed session is imported; the access tools never write memory.
