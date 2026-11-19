# Cited session handoff implementation plan

**Goal** — Produce a bounded, cited Markdown brief from one archived session for manual handoff between coding agents.
**Architecture** — Add a shared archive-only operation in access. Reuse the configured synthesis transport from #82 and the loopback viewer anchors from feature 040.
**Tech Stack** — Python 3.13, uv, Typer, FastAPI, Pydantic v2, httpx, vanilla JavaScript and pytest.
**Branch** — `042-cited-session-handoff` · **Date** — 2026-11-19 · **Spec** — [spec.md](spec.md)

After approval, generate the Spec Kit task list and implement with red → green → refactor. The acceptance path imports a synthetic Claude Code session and manually transfers the CLI or viewer brief to a fresh Codex session.

## Technical context

Reuse the normalized archive through `RawArchive`, `MemoryAccess` and the existing optional OpenAI-compatible synthesis configuration. This is a synchronous, explicitly requested, local-operator read. The same renderer serves Typer stdout and the authenticated FastAPI explorer, with different link bases. There are no new dependencies, stores, write paths, settings or MCP tools. Input and output limits, failure behavior and the positional-link lifetime are specified in the [contract](contracts/handoff.md).

## Constitution check

| Principle | Pre-design and post-design assessment |
| --- | --- |
| I. Raw archive is the source of truth | One normalized archive record supplies all selected session evidence. No archive writes, changes to original preservation or effects on replay. |
| II. Provenance and stable identity | Validate the requested project, exact project tag, stable document ID and normalized record identity before synthesis. Original roles, field positions and message timestamps come from the archive. Requests do not change deduplication, provenance or tags. |
| III. Test-first | Observe focused tests fail first at the archive, synthesis, CLI and browser boundaries. Use native Claude Code import fixtures, a recording synthesizer and browser tests to exercise the evidence and handoff path. |
| IV. Replaceable boundaries | CLI and HTTP use the shared access operation. Access reads through the archive interface and a narrow handoff synthesis protocol. The runtime composes the existing HTTP adapter. No direct Hindsight access and no delivery integration. |
| V. Secrets never reach the memory engine | Only sanitized normalized fields enter the synthesis request and the brief. The authenticated loopback adapter retains its existing binding, Origin/Host, Bearer, CSP and no-store rules under ADR-014. No private text in errors or telemetry, credentials in links, or raw archive reads. |

All five checks pass at design level. No deviation or governance decision record is required. The issue omits the optional alternatives and governance fields. Scope is Phase 3 synthesis under Architecture §22, using the existing post-MVP local explorer within ADR-014.

## Project structure and implementation sequence

The feature documents are the spec, plan, research, data model, quickstart, CLI/HTTP/browser contract and requirements checklist in this directory.

1. **Archive selection and evidence.** Add `access/handoff.py` behind `MemoryAccess.session_handoff` in `access/service.py`. Validate the shared document/project formats and archived identity before exposing anything to synthesis. Build one bounded manifest retaining original field indexes, canonical times, role and tool context. In planned `tests/unit/test_session_handoff.py`, start with tests for foreign/missing/corrupt records, one normalized load, opening and closing evidence, no raw or searchable text, and stable original indexes across skipped messages. Covers FR-001, FR-003 and FR-004.
2. **Cited synthesis and rendering.** Extend `access/synthesis.py` with a handoff operation on the existing transport and wire the narrow protocol in `cli/runtime.py`. Use trusted section/status labels, validate typed entries and exact request selectors, and assemble escaped Markdown and links in access. Test malformed or foreign selectors, unsafe output, explicit acceptance vs proposal, applied vs failed edit, missing command result, contradictory checks, and budget notices. Exercise the existing timeout and response cap using a mock transport before implementing. Covers FR-002, FR-003, FR-004 and FR-007.
3. **CLI and HTTP.** Register `session-handoff` in `cli/__init__.py`; add `POST /api/session-handoff` via shared dispatch in `api/explorer.py`. Extend `tests/contracts/test_explorer_http.py` and add `tests/unit/test_session_handoff_cli.py` to pin plain stdout, fixed errors, request scope, authentication, fixed link origin and no agent paths. Covers FR-005 through FR-007.
4. **Viewer and end-to-end validation.** Add session-only generation and copy to `api/explorer_assets/explorer.js` with existing authenticated request, cancellation and lock behavior. Render Markdown literally. Extend `tests/integration/test_explorer_browser.py` for clipboard success and denial, lock and session-switch races, evidence outside the current page and existing anchor navigation. Update `docs/operations/local-memory-explorer.md` with setup and link lifetime. Run [quickstart.md](quickstart.md) with a synthetic imported Claude Code fixture and record a manual fresh-Codex acceptance result. Covers FR-003 and FR-005 through FR-007.

## Review focus

- Results from failed or unpaired tool calls cannot establish completion. Test claimed versus recorded outcomes in the shared operation.
- An archive can change after generation. Resolve citations through current-snapshot navigation and show the existing unavailable-target state for missing positions.
- Backend output is untrusted. Test injected Markdown links, fake selectors and repeated or overlong content.
- Changing sessions or locking during generation can race a response. Verify the previous selection's result stays cleared and cannot be copied.
- A clipboard denial or an unconfigured synthesizer must leave the ordinary viewer usable. Verify both failure paths.

## Alternatives and open validation

[Research](research.md) records the tradeoffs between a deterministic excerpt, scoped synthesis and cross-session Deep Recall. No product clarification blocks planning. Phase 2 must validate the proposal against sparse and conflicting evidence, actual clipboard behavior, and an actual manual paste into fresh Codex. Anchor positions identify the current normalized snapshot and do not establish semantic entailment. The archive adapter still loads one complete normalized record before selection.
