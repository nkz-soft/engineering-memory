# Research: Codex session source

## R1 — Native format evidence

Decision: Support a bounded JSONL session_meta/response_item dialect; do not promise all Codex histories.
Rationale: OpenAI's rollout fixture includes session_meta with id, timestamp, cwd, then response_item messages and event_msg mirrors. Thus concatenating both duplicates dialogue. The parser contract chooses response items and ignores mirror events.
Sources inspected on 2026-11-03:
- https://github.com/openai/codex/blob/main/codex-rs/app-server/tests/common/rollout.rs
- https://github.com/openai/codex/blob/main/codex-rs/rollout/src/policy.rs
- https://github.com/openai/codex/blob/main/codex-rs/rollout/src/tests.rs
These are moving upstream references, not a stable format guarantee. During implementation pin the exact revision used to synthesize fixtures and verify function/custom tool record fields against protocol definitions before adding support. This is a compatibility validation task, not an unresolved product decision.
Alternatives: Event-only dialogue loses structured tool evidence; accepting every unknown content item silently loses history.

## R2 — Repository integration (read-only research agent findings)

Decision: Reuse normalization/conversation.py Source.CODEX, ToolActivity and generic context; classification/metadata_classifier.py; sanitization/pattern_sanitizer.py.
Rationale: #27 already supports Windows/POSIX cwd, context priority and decoded JSON leaf secret scanning. No dependency or schema change is needed.
Alternatives: Source-specific classification and a schema expansion duplicate existing behavior.

## R3 — Boundaries and replay

Decision: Add ingestion/codex/{parser,source,archive_source}.py; register export and archive readers in cli/runtime.py, source selection/help in cli/__init__.py. Use application/x-ndjson original payloads and identity-checked original replay.
Rationale: Existing Claude Code pattern and tests/contracts/source.py define resumable errors and repeatable reads. A custom iterator advances a file before raising a format error; a generator that closes after an exception is unsuitable.
Alternatives: Normalized-only replay cannot recover parser defects; a separate pipeline duplicates sanitization and idempotency policy.

## R4 — Hash and context

Decision: Preserve canonical v1. Tool request/results affect its hash; repository/cwd do not. Metadata-only corrections require force/replay.
Rationale: Avoid re-extracting existing history to add a source. Document the existing limitation and verify unchanged bytes for other sources.
Alternatives: A hash migration expands scope without fixing an acceptance requirement.

## R5 — Scope and decisions

Decision: Flat operator-provided snapshots; no live history discovery, external output fetch, event-only legacy fallback or subagent aggregation. ADR-011 is available at c1036c7; confirm again before appending.
Rationale: Architecture §22 includes coding agents; §21 does not require acquisition. Issue #19 is closed and #27 merged. No mandatory extension hooks are installed.

## Implementation evidence

Adapter and tests preserve the bounded dialect above. Protocol field evidence is recorded at
OpenAI Codex revision dbaead0106de82bd129a4f6f503d173ad5109f68 in docs/codex.md.
Metadata-only snapshots are supported by the existing empty-message model. The implementation
uses an explicit allowlist for ignored event kinds and reports directory symlinks as resumable
format failures; these decisions were verified by failing regression tests before fixes.
