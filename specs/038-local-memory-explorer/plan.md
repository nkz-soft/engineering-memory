# Local Memory Explorer Implementation Plan

**Branch** `038-local-memory-explorer` | **Date** 2026-11-16 | **Spec** [spec.md](spec.md)

**Goal** Give a local operator a browser view for scoped search, Deep Recall and cited archive messages.

**Architecture** Compose the existing `MemoryAccess` service through `cli/runtime.py::make_read_access`. A same-origin FastAPI adapter under `src/engineering_memory/api/` owns the HTTP session and serves bundled HTML, CSS and JavaScript. The MCP server continues to expose the same service over stdio.

**Tech stack** Python 3.13, uv, Typer, FastAPI, Uvicorn and browser platform APIs. Add explicit web server dependencies and update the lockfile in implementation. Keep frontend assets in the Python wheel.

## Constitution Check

| Principle | Design and verification |
| --- | --- |
| I. Raw archive | Read sanitized conversation pages through the existing access service. Exercise an imported corpus without migration or additional persistence. |
| II. Stable identity | Carry stable document ID, source and original time from service responses. Compare browser, CLI and MCP evidence against the same corpus. |
| III. Test-first | Observe a failing test for each HTTP, launch, evidence and UI behavior before implementing it. Verify browser journeys and an import-to-recall integration with an isolated corpus. |
| IV. Replaceable boundaries | Keep HTTP adaptation separate from memory and archive implementations. Reuse the same access service used by CLI and MCP. Keep the HTTP layer read-only and the stdio transport intact. |
| V. Secrets | Enforce per-launch authentication on data routes, loopback binding, origin and host checks, inert text, no-store and sanitized errors. Record the authenticated transport decision before shipping the listener. |

The web frontend is a Phase 3 extension in roadmap #81. Architecture §21's MVP scope still applies to the MVP. Implementation will add an architecture decision and clarify the Phase 3 browser adapter in Architecture §16 and §22. Amend and version Principle IV to explicitly allow the authenticated local browser adapter to reach memory through the shared read-only service. Record the rationale and transport exception in the feature PR. Principle V's requirement for a decision record and authentication remains in force.

## Review Focus

- Requests from another origin, hostile Host headers, missing or stale credentials and access logs leaking credentials or queries.
- Anchors after page one, corrupt archives, changed messages and a tool index that points to the wrong field.
- HTML and URLs embedded in tool results or generated answer text.
- A slow result arriving after the user has submitted a newer query or changed project.
- Deep Recall disabled or partially available while search and archive reads still work.

## Implementation Sequence

1. **HTTP boundary and launcher.** In `tests/contracts/test_explorer_http.py`, pin the [HTTP contract](contracts/explorer.md), service parity, authentication and fixed errors. In `tests/unit/test_explorer_cli.py`, pin loopback-only launch, fresh credentials, startup failure and lifecycle cleanup. Record the authenticated transport decision and constitution update. Implement `api/explorer.py::create_explorer_app(access: MemoryAccess, *, token: str, authority: str) -> FastAPI` and the Typer `explore` command. Use `make_read_access` for the launcher wiring. Confirm the wheel includes local assets.
2. **Search and transcript.** In `tests/integration/test_explorer_browser.py`, pin project scoping, matching provenance, two pages, empty results, error copy, inert rendering and stale responses. Implement the project and search form, results and paginated conversation panel in `api/explorer_assets/`. Reset results on scope change.
3. **Deep Recall evidence.** Extend contract and browser tests for completed, partial, insufficient, unverified and unconfigured results. Test exact navigation to a late text or tool citation and a stale quote. Render verified claims and coverage with the conversation panel. Resolve a citation by sending the documented conversation request at its message index and checking the field and quote before highlighting it.
4. **Acceptance and operation.** Add a wheel smoke check and local-launch documentation under `docs/operations/`. Run focused tests, Ruff lint and format, the full pytest suite, browser journeys on Windows and Ubuntu, and the parity scenario in [quickstart.md](quickstart.md). Record the actual evidence in the PR.

[Research](research.md) records the transport decision and alternatives. [Data model](data-model.md) maps the existing records into the browser view.
