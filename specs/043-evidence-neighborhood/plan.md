# Implementation Plan: Evidence-backed session neighborhood

**Branch** — `043-evidence-neighborhood` · **Date** — 2026-11-19 · **Spec** — [spec.md](spec.md)

## Summary

Add a one-hop evidence graph to the authenticated local memory explorer. Build a disposable local lookup index from sanitized normalized archives. Query it by exact root and load the current archive record when an operator selects an edge or follows its citation.

## Technical Context

- **Runtime and dependencies** — Python 3.13, uv, Pydantic v2, SQLAlchemy 2 with SQLite, FastAPI, existing HTML/CSS/JavaScript, pytest and the browser test harness.
- **Storage** — Existing normalized archive and a versioned, derived SQLite index under the configured local data directory. The importer and Hindsight remain outside the indexing path.
- **Target** — Existing operator workstation and authenticated loopback explorer under ADR-014. Refresh is an explicit local CLI operation. Graph reads require neither Hindsight nor the synthesis endpoint.
- **Performance** — One indexed adjacency lookup for each requested direction or an equivalent fixed number of bounded queries, at most 30 returned edges, one current archive read per selected edge. No archive enumeration during graph interactions. Validate the documented large synthetic archive and capture timing and query plans.
- **Constraints** — Stable project/repository-qualified identities, conservative recognizers, current-snapshot evidence verification, cancellable browser reads, controlled errors and no sensitive text in operational logs.

## Constitution Check

| Principle | Pre-design and post-design assessment |
| --- | --- |
| I. Raw archive is the source of truth | Archive records are preserved and replay remains independent of the derived index. The index can be rebuilt from normalized records alone and holds no transcript excerpts. |
| II. Provenance and stable identity | Reuse stable document IDs, original event timestamps and exact project tags. Include repository scope where required and validate the current archive snapshot before exposing evidence. Import identity, re-import and tags are unaffected. |
| III. Test-first | Observe focused tests fail before each increment. Use native synthetic source fixtures, an archive fake, a real local SQLite adapter and authenticated browser tests to cover evidence, scope, recovery and limits. |
| IV. Replaceable boundaries | The shared access service reads through the archive and a narrow index reader. CLI composes the writer and iterates the archive outside request handling. HTTP serves the shared read operation under ADR-014. |
| V. Secrets never reach the memory engine | Read sanitized normalized records only. Serve bounded literal text through existing auth, Origin/Host, no-store and CSP controls. Keep originals, raw content, tokens and external calls out of index, links and logs. |

The design complies with all five principles. It needs no governance decision record. The issue omits the optional alternatives and governance fields. This is an operator-facing Phase 3 view under Architecture §22 and ADR-014. Section 21 excludes a custom knowledge graph from the MVP. The proposed read projection uses explicit recorded evidence and leaves knowledge extraction and the memory engine contract intact.

## Project Structure

See [research](research.md), [data model](data-model.md), [browser/HTTP contract](contracts/neighborhood.md) and [quickstart](quickstart.md) in this directory.

1. **Evidence recognition** — Add focused tests in `tests/unit/test_neighborhood_evidence.py` using sanitized outputs of the existing Codex/Claude Code parsers. Implement a deterministic projection in `src/engineering_memory/access/`. Pin successful and failed tool outcomes, explicit continuation resolution, PR URL recognition, path scope and redaction. Cover FR-002 through FR-004.
2. **Rebuild and lookup** — Add a SQLite adapter behind separate refresh and read protocols, compose it through `cli/runtime.py`, and register an explicit command under Typer. Test initial and repeated runs, older archives, interrupted refresh, concurrent readers, missing/corrupt records, high-degree lookup and rollback. Validate that the query uses project/root/order indexes and bounded reads. Cover FR-004 through FR-006.
3. **Authenticated evidence** — Extend `access/service.py` and `api/explorer.py` using the existing dispatch and request hardening. Test stale index entries, project mismatch, indexed IDs and snapshots, import races and rejected requests in unit and HTTP contract tests. Cover FR-001, FR-003 and FR-005 through FR-007.
4. **Browser and acceptance** — Extend `api/explorer_assets/` with session/file entry points, a compact node-and-edge view, keyboard-accessible edge selection and viewer navigation. Extend `tests/integration/test_explorer_browser.py` and document refresh in `docs/operations/local-memory-explorer.md`. Exercise all acceptance scenarios, including stale links, lock, reroot, empty data and high-degree fixture. Cover FR-001 and FR-003 through FR-007.

## Alternatives and open validation

[Research](research.md) compares indexed projection, per-request scans and semantic graph approaches. Product clarification does not block planning. Implementation must confirm evidence recognizer coverage against native synthetic fixtures, verify the query plan, time the large-archive interaction and test viewer snapshot checks across a concurrent archive replacement.
