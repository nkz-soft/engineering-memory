# Data Model

## Existing public values

- EnrichedConversation: immutable conversation, provenance and AnyTag tuple. document_id and content_hash derive from the conversation.
- Conversation: source, source_id, started_at, optional last_activity_at/title and ordered messages. Never reorder by timestamp.
- Provenance: source, source_id, project, optional repository/title, imported_at, importer_version. Imported time remains distinct from conversation time.
- RecallResult: content, validated Provenance and optional score. Several facts may share document identity; the current result exposes identity through provenance source/source_id.

## Internal wire values

- Serialized document: deterministic ordered text with source time/role/tool context, UTF-8 fingerprint and versioned provenance metadata.
- Retain item: content fragment, stable document_id, original timestamp, context, metadata, tags/document_tags and replace/append mode.
- Retain operation: UUID, payload fingerprint, completion deadline and backend completion status. No durable database introduced.
- Recall envelope: verified pinned response mapped to existing results. Missing provenance or malformed content fails with a safe boundary error.

## Lifecycle and validation

New delivery → submit → pending → successful completion. Uncertain submit/poll outcome preserves UUID for identical retry. Confirmed success ends the operation. Changed payload creates a fresh UUID; intentional submission after success also creates a fresh UUID. Terminal failures become boundary errors; no false success on acceptance or failed extraction.

Every part has the same document identity, timestamp, tags and metadata. Splitting preserves all serialized bytes and valid Unicode. Invalid empty content, nonpositive limits and invalid responses are rejected. Whole-request size limits produce explicit failure rather than unsafe independent append calls.
