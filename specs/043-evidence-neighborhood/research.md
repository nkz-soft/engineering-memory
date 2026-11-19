# Research: Evidence-backed session neighborhood

## Indexed adjacency

**Decision** — Use a disposable SQLite projection with an explicit local refresh. Store scoped identity, relation and source coordinates. Read a bounded set of neighbors ordered by source time and a stable tie-breaker.

**Rationale** — The archive interface enumerates documents or loads a known normalized session. It gives no reverse file query. Capping the returned graph alone would still leave file-root request cost dependent on archive size. Archive enumeration may parse envelopes and does not provide a point-in-time snapshot. Display index completion time and partial coverage without promising freshness. The refresh makes a potentially expensive archive scan explicit and keeps it outside authenticated requests.

**Alternatives considered** — Per-request archive scan requires little infrastructure but makes busy-file lookup unbounded. Import-time maintenance would add ingestion coupling and still require a backfill. Hindsight extraction or a graph database adds dependencies and cannot guarantee record-level relations with the current contract.

## Evidence rules

**Decision** — Match source-specific normalized envelopes and explicit textual references with identifiable provenance. Pair tool calls and results using native IDs. Use a successful recognized edit result to corroborate edit paths; use recorded successful commit output with unambiguous repository and object identity; recognize canonical, repository-qualified PR links in supported visible fields. Accept an explicit user-authored continuation with an exact document identifier or an unambiguous supported session reference that resolves within the selected project.

**Rationale** — Claude Code normalization preserves tool use IDs and result/error fields. Codex normalization preserves call IDs and result output. Reuse compatible call pairing and result checks from access/handoff.py with regression tests. For multi-file edits, verify each path against the paired outcome. Both viewer paths already expose message positions and tool fields. The Codex parser does not retain arbitrary session metadata in normalized data, so historical continuation markers can be unavailable. Unsupported tool formats, proposed commands, redacted identifiers, ambiguous paths and unresolved references can be skipped and exercised with fixtures.

**Alternatives considered** — Similarity, assistant summaries and free-form matching could improve recall at the cost of misleading edges. Reading originals at request time would violate the access boundary and could produce evidence the viewer cannot open. The source adapters preserve the operation working directory for recognized tools in the existing normalized request envelope. Replay historical originals to recover missing scope for relative edits and commits where possible.

## Exact viewer navigation

**Decision** — Reuse the viewer selector for message and tool field, with an optional graph-specific snapshot guard checked when serving the destination. Re-read the current sanitized record before showing evidence and again at navigation.

**Rationale** — The existing selector indexes a normalized snapshot. Stable document IDs alone cannot establish that a position still refers to the same message after replacement. The guard binds the selector to the current normalized content and scope without putting evidence or credentials in the URL.

**Alternatives considered** — A plain positional link can land on unrelated content after re-import. Persisting excerpts with the index would duplicate private history without proving that the viewer can still resolve the source.
