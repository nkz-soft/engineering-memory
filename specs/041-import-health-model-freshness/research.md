# Research — Import Health and Project-Model Freshness

## Source outcomes belong in import state

The existing per-conversation record is overwritten by a later failure and cannot describe source enumeration failures, waiting sessions or no-op scans. Keep a bounded aggregate in the SQLite state used by manual and scheduled imports. Use separate attempt and success fields so an interrupted pass can leave the previous completed attempt while keeping already committed imports. An append-only file or a scan of logs adds retention and concurrency concerns. A standalone database would make atomic success updates harder.

`run_import` serves ordinary imports, replay, setup and the acquisition ingestion callback. `run_session_import` runs one pipeline pass per configured source and exposes deferred counts from the capture adapter. Record these observations at the common call sites. Capture lock contention, input validation before source selection and acquisition that never calls ingestion are command-level outcomes. A source-level reader failure within an attempted pass is attributable and must persist.

## Model metadata uses the existing gateway

The current `ProjectModelReader` expands provenance and requires model content. Define a metadata-only projection over the same model identity lookup, including the existing legacy fallback. Preserve explicit backend stale evidence and last successful or failed refresh timestamps. Confirm timestamp and stale-flag semantics in the isolated live suite. When no trustworthy freshness result is available, use unknown. This avoids a transcript scan, a new model refresh or an inference from raw archive modification times.

For a confirmed local project import and comparable refresh time, a strictly newer import establishes stale. Treat an explicit backend stale flag as positive stale evidence. Accept current only for usable affirmative backend freshness with no contradictory local evidence. Absent, equal or uncertain timestamps alone cannot establish current. If the backend cannot establish the meaning of its freshness flag, map that flag to unknown. Positive evidence from a different project never applies.

## Operator interface

Use the local explorer's authenticated JSON dispatcher and existing project scope. A CLI-only extension would require operators to leave the explorer, and a standalone app would duplicate ADR-014 security controls. Refresh on open, explicit read refresh or project change. Keep the existing CLI and MCP contracts.
