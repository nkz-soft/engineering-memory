# Data model: Claude Code sessions

## Input dialect

A file is one session. Nonblank lines are JSON objects; all conversation records use the same
nonempty native `sessionId`. File names never supply missing identity. Conversation records require
unique `uuid` and a timezone-aware `timestamp`. Source start/end are min/max of conversation-record
times, while message order remains file/block order. Empty files yield no conversation; files with
only operational records yield no conversation. Missing identity/time or malformed records fail the
whole session rather than importing an incomplete debugging chain.

`message.content` accepts a string or ordered list of blocks:

| Block | Normalized representation |
|---|---|
| text | Message text with source user/assistant role |
| tool_use | Assistant message, ToolActivity name and deterministic JSON request (`id`, `input`) |
| tool_result | TOOL message, resolved tool name and JSON result (`tool_use_id`, `is_error`, `content`) |
| image/document/other | NonTextPart marker; original bytes retain full block |
| thinking/redacted_thinking | OTHER marker only, not indexed as conversational prose |

One message per block retains mixed text/tool order; all blocks inherit record time. Textual tool
results, including nested text blocks, preserve their order. Unsupported nested blocks add markers;
never decode binary payloads or dereference paths. Serialize JSON before the existing sanitizer so
nested request/result strings are scanned. Represent an empty user/assistant content list as an
empty turn. Parent references remain in originals and never trigger speculative branch traversal.

## Normalized model changes

Conversation adds `repository: Text | None = None` and `working_directory: Text | None = None`.
Both are scanned, serialized and archived, and omitted from canonical v1 coverage. Existing source
payloads deserialize with defaults. ToolActivity, Message, Source enum and canonical schema do not
change. Source.CLAUDE_CODE and its document identity already exist.

The parser chooses first usable context in file order. A repository field is supported only when
explicitly supplied in the bounded dialect; absence is ordinary and cwd alone resolves the project.
Repository provenance uses sanitized `conversation.repository`, falling back to the existing run-wide
repository argument when absent. A cwd is not invented as a repository URL.

## Lifecycle and failures

SourceConversation pairs normalized Conversation with exact full-file OriginalPayload bytes
(`application/x-ndjson`). Directory inputs process sorted top-level `.jsonl` files; nested subagent
folders and symlinks are excluded. A single-file input must be a regular non-symlink snapshot.
A resumable iterator advances past a failed file before reporting SourceFormatError. Unreachable
input uses SourceUnavailable. A repeated native session id within the directory is a duplicate
session failure, never an implicit merge.

Pipeline state remains source id plus content hash. Message changes, including tool errors/results,
change the hash. Context changes alone follow existing metadata refresh policy. Replay filters for
Claude Code originals and reparses these exact bytes through the same parser.
