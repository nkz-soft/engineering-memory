# Research: Hermes memory access

## R1 — Consumer path
Decision: Follow ADR-008 rather than the issue's stale native-provider wording.
Rationale: ARCHITECTURE.md §16.1 and Principle IV explicitly prohibit direct consumer
configuration against Hindsight. The current access module is a placeholder.
Alternatives: Native provider and direct Hindsight MCP rejected; importer-only proof
fails the consumer acceptance goal. No new governance decision is needed.

## R2 — Existing boundaries
Decision: Use MemoryStore.recall and RawArchive.load with dependency injection.
Rationale: RecallResult contains content/provenance/score; provenance has source,
source_id, project, repository, title, imported_at and importer_version. Derive stable
identity from source/source_id and load conversation.started_at for original time.
Archive.load supplies EnrichedConversation and messages in canonical tuple order.
Alternatives: Backend HTTP access from access violates the boundary; import-state
queries add no value for the first two tools. Never call load_original.

## R3 — Filters
Decision: Preserve the existing typed-tag conjunction semantics (adapter currently
uses all_strict). Validate at the surface; no arbitrary engine mode argument.
Rationale: MemoryStore.recall already accepts tags and limit. Other matching modes
would require a separately justified change to the engine-neutral contract.
Alternatives: Fetch-unfiltered then filter locally risks losing relevant limited results.

## R4 — Consumer launch
Decision: Configure a local command/args entry in Hermes mcp_servers. Use an absolute
executable and explicit project/data paths; inherit credentials from the environment.
Rationale: Hermes officially documents stdio subprocess discovery. The planned launch
command is `uv run --project <absolute-checkout> engineering-memory serve`.
Source: https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
Accessed 2026-11-02. This is a proposed recipe until implementation/live validation.

## R5 — SDK and process
Decision: Official MCP Python SDK, stdio only; reserve stdout for protocol and use
stderr diagnostics. Lock a compatible stable SDK version when implementation starts.
Rationale: ADR-008 fixes the SDK; official docs support tool registration and stdio.
Source: https://py.sdk.modelcontextprotocol.io/ (accessed 2026-11-02).
Alternatives: Hand-rolled protocol and third-party server frameworks add maintenance.

## R6 — Configuration and proof
Decision: Add an access-specific settings loader in the existing settings module.
Rationale: load_settings currently requires unrelated extraction LLM configuration;
load_state_path demonstrates narrower loading. Preserve dedicated prefix/path rules.
Decision: Automated SDK tests plus live Hermes evidence, not one as a substitute for
another. Private history is not committed; synthesized ChatGPT fixtures are sufficient
for reproducible public evidence. Operator private-corpus checks remain local.

All design unknowns resolved. Live installed versions and credentials are execution
prerequisites, not assumptions of a passing result.
