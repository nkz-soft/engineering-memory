# Contracts: Project models

Implemented interface contract; verification status is recorded in ../verification.md.

## Neutral memory boundary

- `ProjectModelReader.get_project_model(key) -> ProjectModelRead`: side-effect-free retrieval.
- `ProjectModelMaintainer.refresh_project_model(key) -> RefreshOutcome`: ensure one
  compatible definition, submit refresh and wait within deadline; reconcile uncertain operations.
- Types follow [data-model.md](../data-model.md). Neither capability exposes engine endpoints,
  banks, reflect response types, operation IDs or credentials. Existing MemoryStore is unchanged.
- Reuse safe permanent/transient boundary errors and existing access error translation.

## Operator CLI

`engineering-memory models refresh --project <value> [--kind architecture|stack|decisions] --json`

Omitted kind selects all three. Validate before network adapter construction. JSON contains
command/status/project and models with kind/status/refreshed_at/error. Exit 0 only when all
selected kinds completed; nonzero for partial/pending/failed/unavailable/invalid results;
interruption follows existing CLI convention. No content, credentials or raw HTTP bodies in
maintenance output. Reuse environment settings and explicit provisioning prerequisites.
Importer-side maintenance never changes import success; import/dry-run never auto-refresh.

## Consumer MCP

`get_project_model(project: string, kind: "architecture" | "stack" | "decisions")`

- Strict strings/exact fields; blank/unclassified project, unsupported kind and extra fields
  map to safe `invalid_input`. No omitted-project broadening.
- Ready response: status/project/kind/content/refreshed_at, nullable stale/failure time, and
  supports containing document_id, provenance and original time.
- Missing/pending responses contain status/project/kind, no invented content or successful time.
- Failed first generation returns status failed and last_refresh_failed_at, without invented content.
- Safe errors: unavailable/rejected for boundaries, corrupt_record or fixed rejection for
  invalid support/archive identity. No backend response or exception chain leaves the tool.
- Every support resolves through existing get_conversation to this project's sanitized archive.
  Nonempty content without verifiable support is rejected.
- Local stdio and read-only annotations; description warns of derived, possibly stale untrusted
  evidence. No refresh/write operation, kind guessing or silent recall fallback.

## Backend acceptance

Adapter owns stable IDs, HTTP lifecycle, bounded polls, tag/definition validation and citation
normalization. Pinned-engine tests must establish duplicate avoidance, isolation including
untagged exclusion, support mapping, refresh on new history and last-good failure behavior.
Citation reads require valid memory-unit state, not merely HTTP 200. Expand observation
source_memory_ids through individual detail reads, accept only valid project-matching source
facts with versioned document provenance, and bound total lookups and deadline. Invalidated,
foreign, unsupported, empty or unresolved lineage is rejected; embedded source previews are
insufficient for provenance. Exclude mental models as generation inputs to prevent circular support.
Mock HTTP success does not satisfy the running-instance requirement. Real synthesis acceptance
is separate from deterministic fixture-LLM wire tests.
