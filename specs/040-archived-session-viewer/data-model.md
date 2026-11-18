# Data Model: Archived Session Viewer

No persisted/canonical schema changes.

## Existing records

- Session: document_id, provenance, started_at, ordered normalized messages.
- Message: absolute zero-based index, role, optional sent_at, text, tool_activity tuple and non_text_parts.
- Tool occurrence: local zero-based index, name and optional request/result strings. Native identifiers remain metadata. Null is absent; empty string is present empty content.
- Page: document_id, provenance, started_at, messages, offset, nullable next_offset. Absolute index = offset + local index.

## Browser-only records

- Field view: original sanitized string, optional recognized decoded text/patch, preview and disclosure state. Decode failures preserve literal text. Formatting is never persisted or used as citation evidence.
- Target: project, document_id, message_index, optional tool_index and field (text, tool_request, tool_result). Indexes must be nonnegative safe integers. Tool fields require tool_index; text excludes it.
- Verified anchor: existing target plus quote/timestamp; compare original archived strings, not formatted display.

## State transitions

Locked with optional pending target → unlocked → loading → ready or explicitly unavailable. New navigation aborts prior load. Lock/scope changes clear private UI; stale responses cannot restore it. Validate before expanding/focusing. Back/forward re-resolves targets. Missing data never becomes inferred execution status or invented time.
