# Claude source and CLI contract

ClaudeChatExportSource(path) and ClaudeChatArchiveSource(archive) implement ConversationSource,
with source = Source.CLAUDE_CHAT. read() returns a fresh iterator yielding SourceConversation pairs.
All CS-1–CS-7 rules in tests/contracts/source.py apply without skips, including empty input,
repeatability, uniform source, recoverable SourceFormatError and SourceUnavailable.

Export packaging and mapping are fixed by research.md R3 and data-model.md. Duplicate ids fail the
later record. A recoverable error does not close iteration. Readers close file/ZIP resources on
exhaustion, failure or explicit close; composition owns early exit cleanup.

`engineering-memory import --source claude-chat --export PATH` selects the new export reader.
`engineering-memory import --source claude-chat --from-archive` selects only Claude archived
originals. Omitting --source preserves chatgpt behavior. Only chatgpt and claude-chat are accepted;
other source enum values and unknown strings are usage errors before side effects.

Existing --json, --force, --dry-run, mutually exclusive input selection, exit codes, report fields,
status, provision and serve behavior are unchanged. Recall uses existing source:claude-chat filtering
and get_conversation accepts claude-chat:{id}; no new access method or memory-store endpoint.
