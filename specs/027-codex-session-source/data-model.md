# Data Model

No new domain fields or persistence tables.

- Session identity: session_meta.payload.id becomes Conversation.source_id; Source.CODEX derives codex:{id}. Do not substitute transient runtime session identifiers for native conversation identity.
- Times: native metadata timestamp and timestamped visible records determine original creation/update times. No import clock defaults. Validate monotonic bounds using existing model.
- Context: metadata cwd maps to working_directory; optional source git origin maps to repository if supported and validated. No live Git inspection. Session metadata wins over later per-turn cwd for conversation-wide classification.
- Messages: ordered visible response items map to existing roles/text/non-text markers. Developer instructions map to system role where retained; bookkeeping and encrypted reasoning do not become dialogue.
- Tool activity: deterministic request/result strings preserve native call id, name and payload; outputs retain their position. Missing requests or outputs remain visible as incomplete evidence, never fabricated success.
- Original payload: exact snapshot bytes with application/x-ndjson media type. Archive source reparses bytes and verifies native identity against archive key.
- Import transitions: existing discovered → sanitized/classified/enriched → archived → retained/state recorded; unchanged hash skips extraction; format failure advances to next snapshot. Dry-run and force retain their current semantics.

Canonical v1 stays unchanged: tool evidence changes hashes; context-only changes require force/replay. Sanitize every textual field before external extraction.
