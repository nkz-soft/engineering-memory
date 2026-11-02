# Research: Claude Code source

## R1 — Supported input envelope

**Decision**: Support a fixture-defined UTF-8 JSONL dialect with user/assistant records containing
`sessionId`, `uuid`, `timestamp`, optional `parentUuid`, `cwd`, optional explicit `repository`, and
`message.content` as text or a block list. Skip recognized operational records (progress, summary,
file-history-snapshot, queue-operation, system) as conversational content; preserve them in original
bytes. Unknown record types produce a non-text marker. Exclude sidechains from normalized main history
and add a marker. Reject incomplete lines, conflicting session ids and duplicate conversational uuids.
**Rationale**: The official [hooks reference](https://code.claude.com/docs/en/hooks) identifies session
id, transcript path and cwd, but does not establish a complete stable on-disk session schema. This is
a bounded compatibility decision, not a promise of compatibility with every Claude Code version.
**Alternatives considered**: Reading private local history to infer a schema risks exposing real data;
a vendor SDK introduces a dependency without making older snapshots stable. Use synthetic fixtures.

## R2 — Tool evidence

**Decision**: Preserve each block in order; encode requests as sorted compact JSON containing `id`
and `input`, and results as sorted compact JSON containing `tool_use_id`, `is_error` and textual
`content`. Resolve the result's tool name from preceding calls. An orphan uses `unknown-tool` and
retains the reference; calls without a result remain incomplete. No output is relocated to call time.
**Rationale**: Existing scanned ToolActivity strings participate in canonical v1 and memory rendering.
The official [tool-call contract](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
defines native association and error semantics. Local envelope assumptions remain R1's own contract.
**Alternatives considered**: Pairing by position breaks parallel calls; joining output into prose
loses association; a global tool-schema/hash migration re-extracts unrelated source content.

## R3 — Source context and project detection

**Decision**: Add optional generic `repository` and `working_directory` on Conversation. First usable
context wins. Match configured project aliases against context alone; otherwise slugify repository
basename (strip `.git`) or cwd basename using platform-independent separators. Prefer repository over
cwd. Lowercase ASCII, replace non-slug runs with hyphens, trim edges; empty/`unknown` candidates fall
through to cwd then existing prose rules. Never query the filesystem. Distinct basename collisions
are addressed by explicit configured aliases; no project-registry schema is introduced.
**Rationale**: The classifier already has a chain seam for this exact level (§15). Context must survive
archive replay and not be guessed from prose or tool commands. Enrichment currently has only a
run-wide repository, requiring a small generic per-conversation fallback change.
**Alternatives considered**: Putting paths in the title distorts classification; filename decoding
and current git state invent metadata absent from the source snapshot.

## R4 — Compatibility, privacy and replay

**Decision**: Keep new context outside canonical v1, add it to sanitizer scan coverage, preserve
old-source hashes, and require force/replay for context-only corrections. Parse originals through a
source-specific archive reader. Read one complete file per session; require a quiescent snapshot.
Do not follow attachment or external-tool-output paths. Retain markers for unavailable content.
**Rationale**: Existing canonical coverage is deliberately explicit; adding optional model fields
must not change its meaning. The archive original keeps all unsupported bytes locally. Sanitized
context, requests and outputs use the common pipeline and access surface.
**Alternatives considered**: Hashing metadata changes ADR-006; automatically reading referenced files
expands the trusted input beyond the selected snapshot and makes replay depend on live files.

No unresolved research blockers. Validate this dialect with synthetic fixtures during implementation;
actual recall semantics still require the live integration gate.
