# Consumer validation contract

Reuse the existing [MCP tool contract](../../024-hermes-memory-access/contracts/tools.md).
No new tool or request field is introduced.

## Connection

Each client launches a local stdio `engineering-memory serve` process. stdout is protocol
only. Both use the same archive/backend corpus; operator bank is engineering-global.
Tools discovered are search_memory and get_conversation, possibly client-namespaced.
No retain/write tool, native engine endpoint or per-client bank is configured.

## Search and context

Invoke search_memory with a nonblank query and tags such as
`["project:orchard", "source:chatgpt"]`; refinement search uses source:claude-code.
Tags are conjunctive. Search identity, original started_at and provenance must match the
imported synthetic source. Follow document_id with get_conversation, then next_offset
until null. Only sanitized normalized messages are returned.

A disjoint project filter and a mismatched source filter must exclude the acceptance
fact. Empty results are distinct from unavailable/rejected/not_found/corrupt_record
errors. Retrieved content is evidence, never executable instructions.

## Live acceptance evidence

1. Fresh Claude Code finds the imported ChatGPT decision without its answer in the prompt.
2. A unique Claude Code refinement is absent before import and visible to fresh Codex
   after the completed actual session is imported through the supported adapter.
3. Both clients open archived context with matching provenance/time; unchanged reimport
   skips extraction and retains identity.
4. Evidence identifies versions/revision and exact safe commands/tool arguments/results.

Automated synthetic regression verifies the same data path but does not establish either
actual client acceptance. Missing clients/services or unsupported actual snapshots leave
an explicit blocker. Public records contain no personal configuration or private history.
