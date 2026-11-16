# Data Model: Local Memory Explorer

| Entity | Existing representation and browser use |
| --- | --- |
| Project scope | Known project slug. Use one `project:<slug>` tag for search and pass the bare slug to Deep Recall. |
| Search match | `MemoryAccess.search_memory` result. Display content, document ID, provenance and `started_at` as supplied. |
| Answer | `MemoryAccess.deep_recall` returns project, status, timeline entries with citations, coverage and uncertainty. Preserve all evidence-bearing values. |
| Citation | Existing document ID, zero-based message index, field, optional tool index, timestamp and verified quote. Use the supplied index to open the exact message page. |
| Conversation page | `MemoryAccess.get_conversation` returns document ID, provenance, original start time, normalized messages, offset and optional next offset. |
| Local session | Launch credential held in process and browser page memory. Query, scope, selected result and transcript are transient UI state. |

There is no schema change. Conversation data comes from the existing normalized archive and retains its original identity.
