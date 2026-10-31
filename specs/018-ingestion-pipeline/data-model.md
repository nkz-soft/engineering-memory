# Data model: Ingestion pipeline

## ConversationOutcome

Immutable value with source, optional native source_id and document_id, ImportStatus, UTC completed_at, optional failed stage and safe error category. Error fields exist only for failed outcomes. Unknown parser identity is absent, never synthesized. Original text, exception text and original bytes are not report fields.

## RunReport

Ordered outcomes; counts derived from outcomes; optional safe terminal run error. Counts must reconcile with the outcome length. Success: no failures or terminal error, including empty and all-skipped runs. Partial success: at least one imported/skipped outcome and any item failure or terminal error. Total failure: any failure/terminal error without an imported/skipped outcome. Numeric process exit codes are left to #21.

## Existing persisted values

SourceConversation pairs Conversation with OriginalPayload. Conversation supplies identity and raw content hash. Sanitizer returns a replacement Conversation and RedactionReport; classifier returns ProjectTag. Enrichment constructs existing Provenance and EnrichedConversation with source/project/type tags and optional user/repository metadata.

ImportRecord keeps the hash from the conversation as read, the same document id, source, native id, recorded_at and imported/failed status. Imported is persisted only after archive and retain succeed. Failed is best effort when identity and hash are available. Skipped is report-only. Processing/state failure remains failed even if the remote retain already succeeded; subsequent retry uses the same document id.

## State transitions

Unseen/failed/changed/forced → processing → archived → retained → imported state → imported outcome.
Unchanged imported → skipped outcome without writes.
Any processing failure → failed state attempt when representable → failed outcome → next item.
Recoverable source error → failed outcome → next source pull.
Terminal source error → terminal report error → return prior outcomes.
