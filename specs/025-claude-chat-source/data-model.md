# Data Model: Claude chat source

No new domain or persistence model. This is an explicitly supported export dialect, not a claim
that Anthropic guarantees these fields (see research R1).

| Export value | Existing normalized value | Validation/policy |
|---|---|---|
| Conversation uuid | source_id | Nonempty native string; no generated fallback |
| Constant claude-chat | source | Source.CLAUDE_CHAT; document_id computed as claude-chat:{uuid} |
| name | title | Optional text |
| created_at | started_at | Required timezone-bearing original timestamp, normalized to UTC |
| updated_at | last_activity_at | Optional original timestamp; obey existing model chronology checks |
| chat_messages | messages | Required ordered array; empty allowed; never sort by timestamps |
| sender human / assistant | role user / assistant | Unknown sender fails record |
| Message created_at | sent_at | Optional original timezone-bearing timestamp; no clock fallback |
| content text blocks | text | Join text blocks in recorded order with newline; retain each block's text unchanged |
| Legacy text | text | Used only when content is absent; empty string permitted |
| attachments/files/opaque blocks | non_text_parts | File/image/other marker as appropriate; no bytes/URLs copied into normalized metadata |

Malformed structured content fails rather than falling back silently. Unrecognized fields remain
in the original record; no new inference from account metadata or project IDs. Missing project
classification falls through existing rules. Non-text display names pass through shared sanitization.

`SourceConversation.original` carries the exact JSON record slice encoded as UTF-8, media type
application/json. Replaying this record uses the same parse function as export input. Shared
sanitization, classification, hash and enrichment occur afterward, as for ChatGPT.

Lifecycle: unread record -> normalized/original pair -> shared preparation -> archive -> retention
and state. A malformed record produces SourceFormatError once and advances. Export framing failure
ends reading; unreachable export produces SourceUnavailable. No Claude-specific durable state.
