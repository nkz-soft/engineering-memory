# Claude Code source contract

- `ClaudeCodeSessionSource(path)` implements ConversationSource with Source.CLAUDE_CODE.
- `path` is one saved `.jsonl` session or a directory of top-level snapshots. No automatic home
  directory discovery, recursive subagent ingestion, network access or tool execution.
- `read()` is repeatable and lazy per file; empty input yields nothing. Each yielded original is
  exact session bytes, paired with its normalized conversation. All CS-1–CS-7 checks apply.
- A malformed session raises SourceFormatError from a resumable iterator; the next file remains
  consumable. Error messages never include parsed content, command strings or validation inputs.
- Identity and time come exclusively from source records; valid native ids never use import time
  or a filename fallback. Duplicate ids in one snapshot are errors.
- Block mapping, context precedence and incomplete/orphan tool behavior are in ../data-model.md.
- CLI: `engineering-memory import --source claude-code --export PATH` selects this source;
  `--dry-run` and `--force` retain shared semantics. Use `--from-archive` instead of `--export` to select archived originals.
- `ClaudeCodeArchiveSource` filters archive entries by this source and reparses original bytes;
  it never treats stored normalized output as parser input.
- Metadata classification uses repository, then cwd, before prose aliases; unknown context does
  not prevent ingestion. Enrichment uses per-conversation sanitized repository before run fallback.
- No changes to memory-store, archive-store or state protocols; existing consumers remain generic.
