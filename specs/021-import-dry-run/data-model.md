# Data model: Import dry run

## PreviewRow (immutable)

- source: existing Source enum; source_id/document_id: existing stable identities, nullable only
  for source failures where identity is unavailable.
- project: canonical project tag string; timestamp: original conversation UTC timestamp.
- redaction_categories: sorted unique category names from the sanitizer report, never values.
- decision: would_import, would_skip or failed.
- error: existing fixed Stage/null; required exactly for failed rows.

Successful rows require project and timestamp; fields not reached on failures are null and
categories may be empty. No body, title, original object or raw exception is serialized.

## PreviewReport (immutable)

Ordered rows, would_import/would_skip/failed counts, terminal_error (Stage/null), and status
using existing success/partial_success/failure semantics, counting projected successes.
Empty preview succeeds. No actual imported count is exposed in the preview result.

## Ephemeral decision overlay

Key: (source, source_id). Value: projected latest ImportRecord including original content hash.
Consult overlay first, then durable read-only state. Successful predicted imports replace the
entry; successful skips leave it unchanged. For metadata failures on predicted skips preserve
existing decision state, matching real early skip. For failures on would-import processing,
record only an ephemeral failed decision when needed to mirror real retry/skip behavior.
No overlay entries or failure records are persisted. Discard overlay at end/interruption.
No durable schema change.
