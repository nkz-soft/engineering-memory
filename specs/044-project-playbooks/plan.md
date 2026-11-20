# Reviewed Project Playbooks Implementation Plan

**Branch** — `044-project-playbooks` · **Date** — 2026-11-20 · **Spec** — [spec.md](spec.md)

**Goal** — Publish operator-reviewed, versioned procedures with verifiable links to project history.

**Architecture** — Persist curated artifacts in a dedicated local SQLite catalog with separate writer and reader interfaces. The local CLI owns editing and approval. MCP and the loopback explorer share read operations in `MemoryAccess` and use the normalized archive for evidence.

**Tech stack** — Python 3.13, uv, SQLAlchemy 2/SQLite, Pydantic v2, Typer, the MCP SDK, FastAPI, and existing browser assets and pytest harness. No new dependencies.

## Technical Context

- Reuse exact classified project slugs, stable archive document IDs and the snapshot guard introduced by #89. #82 provides project-scoped recall, which remains an independent retrieval path.
- The local catalog is authoritative for operator approvals. It resides under the configured archive root and needs a backup alongside the archive. Reader startup and requests must work with no catalog yet.
- Bound project lists with cursor paging and indexed queries. Read individual versions by key and validate archive evidence by point lookup. Project discovery does not scan transcripts or call a model.
- The [contract](contracts/playbooks.md) and [data model](data-model.md) define input bounds, publication semantics and failure responses.

## Constitution Check

| Principle | Pre-design and post-design assessment |
| --- | --- |
| I. Raw archive is the source of truth | Each example resolves through the existing normalized archive. The catalog stores curated procedure text and references. It keeps no transcript copies and plays no role in ingestion or archive replay. |
| II. Provenance and stable identity | Preserve exact project, stable archive document ID, original session timestamp and reviewed snapshot per version. Keep the publication timestamp distinct from the source timestamp. Import identities, tags and re-import behavior are preserved. |
| III. Test-first | Observe failing tests before each increment. Cover storage and transactional failures with real SQLite, validate transport contracts and demonstrate the lifecycle from an archived example through both readers. |
| IV. Replaceable boundaries | Separate reader and operator writer interfaces from the SQLite adapter. Both consumers read via `MemoryAccess`. Local CLI writes curated artifacts outside the memory access and ingestion surfaces. Reuse existing stdio and loopback policies. |
| V. Secrets never reach the memory engine | Sanitize title and steps using `PatternSecretSanitizer.redact_text` before storage and preview. Validate sanitized output, render it as literal content, use normalized evidence only, and keep input bodies and secrets out of diagnostics. No engine writes or synthesis calls. |

Architecture §22 places the feature in Phase 3. The operator writes local curated artifacts through the CLI and the access boundary stays read-only under §21, ADR-008 and ADR-014. The issue omits the optional governance and alternatives fields. The proposal entails no constitution deviation, stack change, Hindsight contract change or new history source. See [research and alternatives](research.md).

## Project Structure and Verification Sequence

All implementation increments use red, green and refactor. The [quickstart](quickstart.md) defines the final operator acceptance run. Phase 2 expands this sequence into tasks after approval of this plan.

| Increment | Files and interfaces | Acceptance and test entry points |
| --- | --- | --- |
| Draft and publication | Add `playbooks/models.py`, `playbooks/interface.py`, `playbooks/sqlite.py` and `playbooks/service.py` under `src/engineering_memory/`. Compose the local writer in `cli/runtime.py`. Add `cli/playbooks.py` and register its Typer group in `cli/__init__.py`. Writer exposes `stage`, `review` and conditional `approve`. | `tests/unit/test_playbook_store.py` and `tests/unit/test_playbook_cli.py` pin sanitization, input bounds, source validation, staged-order preservation, stale draft and source conflicts, concurrent publication, rollback and retry after a lost response. FR-001, 002, 006, 007. |
| Shared reads and MCP | Add catalog reads to `access/service.py`. Compose a reader in `cli/runtime.py` and register two read tools in `access/server.py`. Generalize the existing guarded archive request for both transports and keep legacy unguarded `get_conversation` valid. Use the same guarded result for browser and MCP. | `tests/unit/test_access_playbooks.py`, `tests/integration/test_access_mcp.py` and `tests/integration/test_deep_recall_mcp.py` pin project isolation, exact version lookup, bounded cursors, empty catalog, unchanged ordinary retrieval, additive tools and sanitized source opening. Update tool discovery assertions in `tests/integration/test_access_mcp.py` and `tests/integration/test_coding_agent_access.py`. FR-003 through 007. |
| Explorer and release validation | Add authenticated reads in `api/explorer.py` and a Playbooks panel in `api/explorer_assets/{index.html,explorer.js,explorer.css}`. Reuse project scope and guarded conversation navigation. Update `docs/operations/local-memory-explorer.md` and `docs/operations/coding-agent-memory.md`. | Extend `tests/contracts/test_explorer_http.py` and `tests/integration/test_explorer_browser.py` with the two-version acceptance scenario, scope switches, locked access, unavailable snapshots and text rendering. Run the [quickstart](quickstart.md) on a synthetic archive. FR-003 through 007 and SC-001 through 004. |

## Review Focus

- A stale or concurrently replaced draft cannot be approved using an old revision token. Storage verifies the pending token during publication.
- Source drift before approval blocks publication. The stored snapshot guard also detects changes between evidence validation and a later read.
- A lost response after commit cannot create another version on retry. The approval identifier is unique per project and playbook.
- A missing catalog reads as empty. An unreadable or incompatible catalog returns a controlled unavailable result.
- Rapid project switches cannot render an earlier project's in-flight response. Project mismatch and changed source are covered in the browser flow.

## Open Validation

Implementation must verify packaged CLI registration, two-writer behavior using separate SQLite connections, and source guarding on live stdio and authenticated loopback requests. These are validation items for the approved implementation phase.
