# Codex Source Contract

## Operator surface

Planned CLI selection: `--source codex` on the existing import command. Existing default remains chatgpt. Accept an explicit JSONL file or flat directory of JSONL snapshots. No automatic lookup of private Codex storage.

## Supported baseline

UTF-8 JSONL, one native conversation per snapshot. Require consistent session_meta with payload.id, payload.timestamp and optional payload.cwd; preserve original timestamped record order. Metadata-only sessions yield an empty conversation, as permitted by the shared model.

Select response_item.payload as visible transcript authority: message roles user/assistant/system/developer, textual input_text/output_text, and supported non-text markers. event_msg types user_message, agent_message, agent_reasoning, token_count, task_started, task_complete and turn_aborted are allowed but add no dialogue; other event types fail. Turn context and compaction bookkeeping do not add dialogue. Ignore a documented allowlist of bookkeeping records. Reject unsupported content-bearing response types with a safe format error; keep original bytes available on successful snapshots for future reparse.

Support function_call/function_call_output and custom_tool_call/custom_tool_call_output only after verifying their exact fields against a pinned upstream protocol revision. Preserve call_id, tool name, arguments/input and output as deterministic ToolActivity strings in order. Unmatched outputs and calls without outputs remain explicit evidence. Nested JSON values must remain available to the shared sanitizer. No external paths are dereferenced.

Compaction metadata must not inject replacement_history or summaries as additional dialogue. Import the visible records actually present once; do not reconstruct missing pre-compaction history. Event-only histories fail explicitly as unsupported, rather than succeeding as empty history.

## Shared boundary

Implement ConversationSource CS-1–CS-7 via tests/contracts/source.py. Repeatable reads, empty-directory behavior, stable identity and original payload are mandatory. Advance failed file before SourceFormatError; filesystem unavailability uses SourceUnavailable. Reject symlinks and duplicate native ids in deterministic sorted file order. Errors omit private content and credentials.

## Pipeline and replay

Register both export and original-archive readers in cli/runtime.py. Original replay validates parsed source/id equals archive identity. No raw snapshot or source-specific parser bypasses shared sanitization and classifier policies. Verify source:codex, project tags, stable document id, real timestamps and importer version in retained metadata.

## Acceptance matrix

Unit: text/order/tool association, mirror deduplication, context precedence, malformed/truncated records, Unicode, unknown records, metadata-only and event-only inputs.
Contract: all shared source checks, valid/invalid/valid iteration and original bytes.
Integration: dry-run, force, unchanged skip, changed tool-output update, original replay without source files, no private text in logs, sanitizer secrets in every new field.
Live: synthetic fact recall through the access surface under source:codex and project filters; verify identity in the provisioned shared bank and cross-source isolation.
