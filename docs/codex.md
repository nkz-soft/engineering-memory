# Importing Codex session history

Stage complete UTF-8 JSONL snapshots in an ignored `data/` directory. Select one file or a flat
directory of `.jsonl` files; directory import is nonrecursive and sorted. Symlinks report
resumable format failures and are never followed.
Selecting a symlink directly reports one format failure. Never import a file still being written.

```bash
uv run engineering-memory import --source codex --export data/codex --dry-run --json
uv run engineering-memory import --source codex --export data/codex --json
uv run engineering-memory import --source codex --from-archive --force --json
```

The source emits `source:codex` and `codex:{native-conversation-id}` through shared enrichment.
Session metadata `id` supplies identity, rather than any runtime `session_id`. Original dates are
retained. Recorded `cwd` and optional `git.repository_url` supply level-1 metadata classification
before prose aliases; no live filesystem/Git lookup occurs. Per-turn cwd changes do not reassign
the conversation-wide project. Missing context uses existing alias/fallback classification.
Context-only corrections require force/replay because canonical v1 excludes cwd/repository.

## Supported dialect

The fixture-backed baseline uses `session_meta` and timestamped `response_item` envelopes.
Metadata requires native `id` and timezone-bearing `timestamp`. Messages support user, assistant,
system and developer (mapped to system), ordered input_text/output_text blocks, and image/audio
presence markers. Binary payloads and URLs are not copied into the normalized conversation.
Metadata-only snapshots normalize to empty conversations. Event-only dialogue is rejected.

`function_call` and `custom_tool_call` preserve call_id, name and arguments/input; matching output
records preserve call_id and textual/structured text output. Orphan outputs use `unknown-tool`;
unfinished calls keep an absent result. Duplicate call IDs and conflicting metadata are errors.
Requests/results remain in record order. Incomplete function argument JSON remains text.
Decoded JSON arguments and outputs pass through the existing sanitizer, including nested secrets.

Legacy `event_msg` records `user_message`, `agent_message`, `agent_reasoning`, `token_count`,
`task_started`, `task_complete` and `turn_aborted` add no dialogue.

Codex Desktop rollouts can also record `additional_tools` declarations, `world_state` snapshots,
`token_usage_record` accounting, and `thread_settings_applied` checkpoints. Their payloads stay in
the original archive and do not change conversation dates. For `item_completed` events, text
`UserMessage` and `AgentMessage` items require a same-role response in the same turn, before or
after the event.
Each distinct completion requires its own match.
A `CommandExecution` from unified-exec startup or interaction is kept in the original when the
same turn contains a paired model shell request and result. The original UI item ID and the model
`call_id` can differ. Normalization uses the model's `call_id` and leaves the event's display
details in the original. Other completion kinds and event-only transcripts are unsupported.

Manual import, automatic capture and archive replay use this same bounded dialect. Unknown event
and completion types fail the snapshot. `turn_context`, `compacted` records and internal
`reasoning` response items do not add dialogue.
Compaction summaries/replacement history are not appended or used to reconstruct missing history.
Unknown envelope or content-bearing response types fail the snapshot explicitly. There is no
claim of universal Codex version compatibility; add synthetic fixtures before expanding support.

No private-session discovery, live tailing, external output-file reads, event-only legacy fallback,
subagent aggregation or encrypted reasoning decoding is performed. Exact original bytes are archived
as application/x-ndjson, independently of sanitized normalized content and memory extraction.
Archive replay reparses originals and checks identity; no source files are needed. Originals stay
private and must not be committed. Access serves sanitized normalized content only.

## Compatibility evidence and checks

Baseline fields were checked against OpenAI's protocol source at revision
`dbaead0106de82bd129a4f6f503d173ad5109f68`:
[models.rs](https://github.com/openai/codex/blob/dbaead0106de82bd129a4f6f503d173ad5109f68/codex-rs/protocol/src/models.rs).
The Desktop extension follows the upstream
[response model](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/models.rs),
[turn items](https://github.com/openai/codex/blob/main/codex-rs/protocol/src/items.rs) and
[rollout persistence policy](https://github.com/openai/codex/blob/main/codex-rs/rollout/src/policy.rs).
Fixtures contain only invented sessions and tool results.

```bash
uv run pytest tests/unit/test_codex_source.py tests/contracts/test_codex_source.py tests/integration/test_codex_cli.py
uv run pytest tests/integration/test_codex_live.py
```

The second command skips unless `ENGINEERING_MEMORY_LIVE_CONTRACT=1` is set and an isolated live
contract service is provisionable at `ENGINEERING_MEMORY_LIVE_STORE_URL` (default localhost:8889).
It creates and deletes a synthetic test bank and verifies root-cause recall with source/project
filters, negative filters and sanitized archive access. A skip means live acceptance is unverified.

## Reading shared memory from Codex

To retrieve imported history, follow the [coding-agent memory setup](operations/coding-agent-memory.md).
Codex reads the same corpus as other clients through the read-only MCP access surface, using
project/source filters. Imported Claude Code refinements are available after their import completes.
