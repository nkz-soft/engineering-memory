# Data Model

Existing public values remain EnrichedConversation, Conversation, Provenance,
AnyTag and RecallResult. Document identity is source-derived and time is original.

Internal item: full ordered conversation JSON, stable document_id, timestamp,
replace mode, tags and versioned string metadata containing validated provenance.
One async item per operation; extraction chunking belongs to the engine. Requests
above the configured total UTF-8 byte cap fail before I/O.

Pending state: document identity maps to exact item fingerprint and UUID, bounded
to 128 uncertain documents. Same pending payload reuses UUID; changed payload
gets a fresh UUID; confirmed completion/terminal failure clears its entry. No
adapter database is introduced; cross-process retry coordination belongs to #20.

Lifecycle: serialize/validate -> submit -> poll -> complete. Acceptance is not
completion. Uncertain outcomes preserve retry identity. Recall reconstructs typed
provenance only from valid versioned metadata and verifies document identity and
requested tags; it never fabricates values missing from the engine response.
