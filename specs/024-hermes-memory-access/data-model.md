# Data model

No persisted entities or migrations are added.

- SearchRequest: nonblank query; typed tags, default empty; integer limit 1..100,
  default 10. Reject invalid namespaces/values using existing normalization models.
- MemoryMatch: content, deterministic document_id, existing complete provenance,
  original conversation started_at from normalized archive, optional relevance score.
  Score is only comparable within a single result set; do not threshold it.
- ConversationRequest: stable source-prefixed document_id, offset integer >=0 default
  0, page_size integer 1..100 default 50. Reject booleans as numeric input.
- ConversationPage: document_id, provenance, original started_at, ordered normalized
  message slice, offset, next_offset or null. Preserve roles, text, optional time and
  existing tool/non-text representation. No original payload or storage paths.
- SafeFailure: stable code and fixed safe description. Invalid input, not found,
  corrupt record, dependency unavailable and rejected read are distinct.

A search match links to the same archive identity used by get_conversation. Reads
have no state transitions. Missing archives fail explicitly rather than fabricate
provenance. Paging is per request, not a snapshot across concurrent re-imports; users
should repeat from offset 0 if the source changes while paging.
