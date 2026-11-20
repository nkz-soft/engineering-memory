# Research and Design Decisions

## Publication boundary

**Decision** — The operator stages JSON, reviews sanitized content in the CLI, and approves an exact revision token. The browser and MCP call the shared catalog reader.

**Rationale** — The constitution prohibits writes through memory access, and ADR-014 defines an authenticated loopback browser adapter for reads. The existing Typer surface provides a local operator boundary. It also supports drafts prepared with external tools without granting MCP a writer or adding a generation dependency.

**Alternatives** — Browser editing would require a new write boundary and governance review. Automatic extraction from recall can be added as a draft producer if there is a separate need for it. Human approval remains explicit.

## Local catalog and discovery

**Decision** — Use dedicated SQLite storage, latest-approved project listing and explicit approved version lookup.

**Rationale** — A transaction can insert the immutable version and clear the corresponding draft together. A dedicated catalog makes its backup requirements clear and keeps draft data outside ingestion, ordinary search and synthesis. The existing neighborhood database is disposable and must remain independently rebuildable.

**Alternatives** — JSON files would need their own locking and crash recovery for concurrent staging and approval. Writing draft or approved records to Hindsight would couple publication to ingestion and provenance policies. Project listing covers discoverability without a change to recall ranking.

## Archived examples

**Decision** — Resolve source document IDs against the normalized archive at staging. Record their project, original time and existing snapshot hash. Confirm each at approval and reuse the archive guard from #89 when opening the source.

**Rationale** — An archive record can change on reimport. Guarded navigation preserves what the operator approved and avoids showing current content as the original example. The viewer uses existing archive pagination.

**Alternatives** — Document ID alone could show newer content under an old approval. Copying each transcript into the catalog would duplicate private history and add retention obligations. The catalog retains provenance and reports an unavailable original snapshot when the archive can no longer serve it.

**Roadmap context** — The [issue's Hansard reference](https://www.hansard.dev/releases/) provides examples of review and artifact-to-conversation navigation. The proposed workflow follows the repository's own CLI, archive and explorer contracts.
