# Data model: Project mental models

## ProjectModelKey

`project`: exact existing classified value, nonblank, not unclassified.
`kind`: closed enum `architecture`, `stack`, `decisions`.
Logical identity `(project, kind)`; private engine ID `em-pm-v1-` plus SHA-256 of canonical
JSON `[project, kind]`. Never use generated content or lossy slug normalization for identity.
Definition tags contain precisely `project:<value>`; no new tag namespace.

## ProjectModelDefinition

Key, fixed display name, standing synthesis question, definition version and token budget.
Questions require supported current state, chronology, uncertainty and references. Definition
updates do not change conversation identity. Adopt only a definition whose identity/tags and
managed configuration are compatible; unexpected collisions are rejected.

## ProjectModelSnapshot

Key, nonblank completed content, aware `refreshed_at`, tuple of supports, nullable `stale`,
nullable `last_refresh_failed_at`. Null stale means unknown, not fresh. A failed newer refresh
preserves last-good content and timestamp, with failure visible. Empty initial content is pending,
not a completed snapshot. Successful refresh time is not the time of source conversations.

## ModelSupport

Stable `document_id`, existing validated Provenance, original conversation time; deduplicate
by document ID. Resolve backend fact/observation links inside the adapter, then validate exact
project and archive identity in the reader. Never manufacture one provenance for a synthesis.
Reject nonempty content whose supporting conversation references cannot be verified.

## ProjectModelRead and RefreshOutcome

Read result discriminates `ready`, `missing`, `pending`, `failed`; only ready contains a snapshot.
Failed first generation carries a safe last_refresh_failed_at and no successful snapshot.
Ready may be stale or carry a newer failed-refresh time. Boundary errors remain safe neutral
permanent/transient exceptions. Refresh outcomes contain project/kind, `completed`, `pending`,
`failed` or `unavailable`, safe optional error category, successful time only when confirmed.
Engine model/operation identifiers stay private. All-kinds maintenance has three independent results.

## State transitions

Absent → submitted/pending → ready. Ready → refreshing → ready(new snapshot).
Failure preserves old ready plus failure metadata, or no successful snapshot if generation never
completed. Timeout is uncertain/pending: reconcile deterministic identity and outstanding operation
before resubmission. No atomic three-model guarantee and no import-state schema changes.
