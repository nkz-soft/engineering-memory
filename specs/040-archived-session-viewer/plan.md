# Implementation Plan: Archived Session Viewer

**Branch**: `040-archived-session-viewer` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)
**Input**: Issue #86. Planning only; implementation requires approval.

## Summary

Extend the existing local explorer evidence reader. Present known normalized tool envelopes readably, show recorded textual diffs, collapse large fields and add fragment-based targets. Reuse MemoryAccess.get_conversation and its pagination without new endpoints, archive schema, synthesis or dependencies.

## Technical Context

**Language/Version**: Python 3.13 and existing browser JavaScript/CSS/HTML.
**Primary Dependencies**: Existing FastAPI, Pydantic v2, uv, pytest and Playwright harness.
**Storage**: Sanitized normalized local archive through RawArchive and MemoryAccess; no new persistence.
**Testing**: pytest unit, HTTP contract and opt-in real-browser integration suites.
**Target Platform**: Authenticated IPv4 loopback explorer in Chromium/Edge.
**Project Type**: Modular monolith with bundled browser adapter.
**Performance Goals**: Keep 50-message browser pages (service maximum 100); render requested page only. Preview at most 20 lines/2,000 characters. Collapsing bounds visible output, not archive I/O or response bytes.
**Constraints**: Preserve ADR-014 Host/Origin/authentication, CSP, no-store, in-memory token and fixed errors. No original reads, live git, execution or remote assets.
**Scale/Scope**: One session/page at a time; both coding sources and legacy prose regression coverage.

## Constitution Check

| Principle | Before research and after design |
| --- | --- |
| I. Raw Archive Is the Source of Truth | All evidence comes from normalized archives; no secondary store or regenerated repository diffs. |
| II. Provenance and Stable Identity | Preserve document IDs, original order/time and project provenance; current-snapshot positional links, stronger quote/time checks for citations. |
| III. Test-First | After approval observe each regression fail before implementing its slice, then green/refactor. No code in this phase. |
| IV. Replaceable Boundaries | Browser uses existing authenticated conversation route and shared service; no direct archive/Hindsight access. |
| V. Secrets Never Reach the Memory Engine | Sanitized fields rendered as text; no original fallback, token in URLs/storage, content logs or external renderer. |

Both checks pass, no deviations. Phase 3 extends ADR-014, not the MVP web frontend. Missing governance fields do not authorize policy changes; none proposed. No ADR/constitution amendment needed.

## Project Structure

- src/engineering_memory/api/explorer_assets/explorer.js: presentation, disclosure, diff recognition, fragment targets and citation integration.
- Sibling explorer.css/index.html: accessible styles and navigation/status shell as necessary.
- src/engineering_memory/access/service.py and api/explorer.py: existing contracts expected unchanged; strengthen regression tests.
- tests/integration/test_explorer_browser.py: real browser synthetic cases.
- tests/contracts/test_explorer_http.py, tests/unit/test_access.py and tests/integration/test_coding_agent_access.py: boundary regressions.
- docs/: link usage and snapshot limits.
- This directory: spec, plan, research, data-model, contracts, quickstart, requirements checklist. tasks.md deferred until approval.

## Alternatives Considered

1. Extend current reader (proposed): reuse security, citations and archive responses with limited presentation/navigation work.
2. Dedicated session API/schema: future indexing benefits, but introduces contract/hash/migration scope without missing evidence here.
3. Standalone runs application/live git reconstruction: duplicates access policy or replaces historical evidence with current files; rejected.

The issue supplies no alternatives. These are proposals for approval, not previously accepted user decisions.

## Implementation Sequence After Approval

1. Write failing synthetic browser cases for both source envelopes, parallel calls, separate/orphan/absent/empty/error results and legacy strings. Add conservative presentation helpers; retain literal source fields and order.
2. Write failing cases for unified/apply_patch text, recorded Edit old/new fields, unknown shapes and hostile markup. Add readable recorded-diff presentation with exact raw text available; never claim a patch was applied.
3. Write failing 10,000-line, keyboard disclosure and hidden-target cases. Add bounded previews and native accessible expansion without silent truncation.
4. Write failing navigation cases at 0/49/50/100, refresh/unlock/back/forward, malformed selectors, wrong scope, missing targets, invalid quote/time and rapid lock/navigation. Add fragment links and exact-page loading, focus and expansion. Preserve verified citation checks.
5. Exercise real HTTP/shared-service reads with synthetic normalized archives. Verify auth/Host/Origin/no-store, fixed errors and sanitized-only data. Check cancellation, zero execution/external fetches and existing search/prose/Deep Recall/decision-history behavior. Update docs and run quickstart checks.

Each slice follows red → green → refactor. No tasks generation before approval.

## Risks and Review Focus

- Tool JSON is source-specific presentation data, not a new domain schema; unknown/malformed fields remain literal.
- Calls/results can occupy separate messages/pages. Do not merge or infer global completion.
- Normalization groups prose and tool tuples; finer original block interleaving cannot be recovered by the viewer.
- Large fields still consume response/DOM memory when expanded; streaming is outside scope.
- Plain links select current archive positions; only verified citations detect changed quoted evidence. Immutable revisions require separate work.
- URLs contain identifiers/positions only. Lock clears private UI but can retain the pending fragment for unlock.

## Complexity Tracking

No violations, new dependencies, services or persistence.
