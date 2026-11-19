# Session handoff contract

## CLI

```text
engineering-memory session-handoff DOCUMENT_ID --project PROJECT [--explorer-origin http://127.0.0.1:PORT]
```

Print UTF-8 Markdown on success. Diagnostics go to stderr with a nonzero exit on failures and no partial Markdown. Default citations are fragment selectors; an explicit origin must use HTTP with a literal loopback address and explicit port and contain no credentials, path beyond optional slash, query or fragment. The command does not start the explorer.

## Explorer

`POST /api/session-handoff` accepts exactly `document_id` and `project` as JSON and returns `{"markdown":"..."}`. Use existing host, origin, Bearer, body cap, no-store headers and fixed errors. Build absolute links from the server's validated listener authority. Reject malformed input, map missing or wrong-scope selection to the same not-found response, and distinguish unconfigured synthesis from generation failure using fixed codes. Do not accept a link origin in the JSON. No new MCP tool.

The session view presents Generate handoff and, after success, a selectable plain-text brief and Copy Markdown control. Copy uses the clipboard on explicit interaction. Denial leaves selectable text and a manual-copy instruction. Clear the result and invalidate pending requests on session switch or lock. Ignore obsolete responses, including after a lock and reopen of the same session.

## Evidence and output

- One normalized load. Consider all positions for sessions up to 256 messages. For longer sessions, consider the first 128 and last 128 in original order, processing by alternating oldest and newest so the prompt budget cannot be consumed entirely at one end. Prefer message text within a position and preserve tool request and result as distinct fields. Include at most 128 nonempty evidence fields, 1 KiB UTF-8 per field and 24 KiB of sanitized field text total. Mark partial coverage for any skipped or clipped evidence. These caps apply after archive decoding and before prompt serialization.
- Require a closed result schema with at most 12 entries, up to three selectors per entry and at most 300 Unicode characters in each paraphrase. Reject malformed responses and out-of-manifest references. Preserve the adapter's 30 s timeout and 16 KiB response cap. The adapter receives bounded evidence and canonical context, without access to tools. A successful check or applied edit requires recorded outcome evidence. A tool request or unsupported assistant assertion can establish an unknown, with attribution where available. Use both sides of a recorded conflict.
- Application code emits the headings Goal, Confirmed decisions, Touched files, Checks and Open questions. Escape model and archive text as inert Markdown, suppress arbitrary URLs and never accept model-provided markup or link destinations. Use the feature 040 selector with document, project, message and optional tool/field. Link characters must be safely encoded. Keep all headings within the 8 KiB limit by dropping complete overflow entries and showing an omission notice. An empty section explicitly says what could not be established.
- Links address the current archived position, using the existing sanitized viewer. They do not bypass authentication. Reopening the explorer may require using the selector at its new origin. Generation and clipboard copying perform zero agent launches, resumes, or messages.
