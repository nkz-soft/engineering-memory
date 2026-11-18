# Session Viewer Contract

## Existing transport

POST /api/conversation with Bearer authentication, exact Origin/Host and JSON {document_id, offset, page_size}. Offset >=0, page_size 1–100 (browser 50). Response remains {document_id, provenance, started_at, messages, offset, next_offset}. Existing fixed errors, no-store and sanitized-only service boundary remain. No new HTTP/MCP operations.

## Browser target

Synthetic example:

`/#view=session&project=orchard&document=codex%3Aexample&message=100&tool=0&field=tool_result`

- Encode with URLSearchParams. Require view=session, project, document and message. Optional tool and field; default field=text.
- Indexes are decimal nonnegative safe integers. Tool fields require tool; text excludes it. Reject duplicate/unknown/inconsistent keys and fragments exceeding 4 KiB with a fixed unavailable-target state.
- Validate identifiers/project through existing service conventions and against response. A URL is not authorization. No credentials, quotes, commands or output in URLs/storage.
- Preserve pending selector through unlock; only authenticated reads resolve it. Copy-link actions generate message/tool-field selectors. Per-launch origin must have a running explorer; stable hosting is not promised.
- Fetch offset=message/page_size=50. Verify document, offset, project and message/tool existence. Null field is a valid explicit missing-data target; nonexistent index is unavailable. Expand, highlight and focus target.
- Existing verified citations additionally require original quote/time checks before display. Keep the verified anchor in memory, not copied URLs; do not weaken it to positional navigation.
- Ordinary links select the current archive snapshot. Link help states this limit; replaced positional content is not historically verified without a citation.

## Presentation

Preserve normalized order. Known source envelopes show readable name/request/result/native IDs/error metadata. Unknown shapes stay literal. Separate call/result occurrences remain separate. Show recorded patches/old-new values accurately and keep exact raw sanitized fields available; never apply changes or read referenced files.

Beyond 20 lines/2,000 characters show bounded preview with keyboard-operable complete expansion. Targets expand their field. All recorded content uses text nodes, without executable HTML/Markdown, automatic external links or external fetches. Preserve non-text markers, absent versus empty results, cancellation and lock clearing.
