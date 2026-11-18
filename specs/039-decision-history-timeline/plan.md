# Source-Backed Decision History Implementation Plan

**Branch** `039-decision-history-timeline`  
**Date** 2026-11-16  
**Spec** [spec.md](spec.md)  
**Issue** [#85](https://github.com/nkz-soft/engineering-memory/issues/85)

## Summary

Extend the local browser's Deep Recall operation with an explicit decision-history mode. The shared read service retrieves bounded project evidence, validates a structured synthesis, and builds chronology and message links using server-derived citation anchors. The browser renders the decision detail through its existing authenticated workspace and conversation viewer.

## Technical Context

Python 3.13, uv, Pydantic v2, FastAPI, existing browser JavaScript and CSS, pytest and the existing Playwright browser harness. No additional runtime dependencies or persistence. One project and topic per lookup. Reuse Deep Recall's existing search and archive limits, the 30-second synthesis timeout and 16 KiB synthesis-response limit. Keep the existing authenticated IPv4 loopback transport and the established synthesis endpoint configuration.

## Constitution Check

| Principle | Design and review check |
| --- | --- |
| I. Raw Archive Is the Source of Truth | Recalled items locate candidates. All displayed evidence resolves to normalized archived messages and no new history store is written. |
| II. Provenance and Stable Identity | Keep existing document IDs and verify both project provenance and archive tags. Bind each citation to its message and original time. Never derive an event date from import time. |
| III. Test-First | Write each failing test and observe red before implementing its slice. Verify shared service, synthesis transport, HTTP and browser boundaries as described below. |
| IV. Replaceable Boundaries | Keep memory, archive and synthesis behind their existing interfaces and reach them through `MemoryAccess`. The existing browser route and access transport retain their policies. |
| V. Secrets Never Reach the Memory Engine | Consume sanitized records only, use the configured synthesis boundary, preserve exact Host, Origin and credential checks and fixed errors. Render output as text and preserve the existing cache and logging policies. |

Phase 3 under Architecture §§21–22. The issue supplied no governance ticks. The design preserves the technology stack, sources, bank, tags and ADR-014's three browser read operations. Post-design check against the [model](data-model.md) and [contract](contracts/decision-history.md) found no deviations.

## Project Structure

- `src/engineering_memory/access/deep_recall.py` owns shared bounded evidence gathering and anchor verification.
- `src/engineering_memory/access/decision_history.py` owns the decision draft, validation, ordering and result assembly.
- `src/engineering_memory/access/service.py` validates the request and dispatches through `MemoryAccess.decision_history(**arguments) -> dict`.
- `src/engineering_memory/access/synthesis.py` adds the decision instructions through a dedicated `synthesize_decisions(query, passages, times) -> object` method using the existing transport and configured credentials. Ordinary `synthesize` keeps its prompt and signature.
- `src/engineering_memory/api/explorer.py` validates the optional browser mode. `api/explorer_assets/{index.html,explorer.js,explorer.css}` supply the action and render the detail with the existing evidence reader.

## Alternatives Considered

The issue supplied no alternatives. [Research](research.md) covers the standing snapshot, free-form synthesis, persisted event indexing, browser routing and time provenance.

## Review Focus

1. Provenance can disagree between memory and archive even for a matching project. Assert rejection before synthesis.
2. An old supporting excerpt can precede the actual adoption message. Assert that only the action timestamp orders that event.
3. Conflicting versions can have equal timestamps or missing dates. Assert visible ambiguity and independently cited accounts.
4. An older archive can change between rendering and opening. Assert that an invalidated message, quote or original timestamp yields the existing unavailable state.
5. A late browser response can arrive after a scope change or lock. Assert that neither events nor citations return to the cleared workspace.

## Implementation Sequence After Approval

### 1. Shared evidence and structured synthesis

Cover FR-002 through FR-005 in `tests/unit/test_decision_history.py` and transport cases in the existing Deep Recall unit tests. Start with failing assertions for the four event kinds, cross-session supersession, prior version, reason and action-message timestamp. Add separate assertions for equal instants with differing offsets, missing or disputed time, conflict-only results, duplicate evidence, foreign or mismatched provenance, malformed draft and bad selectors or quotes. Check empty evidence and budget termination. Check that synthesis receives only bounded sanitized selector passages and timestamps through the same configured endpoint.

Implement `decision_history(memory, archive, synthesis, query, tag) -> dict`. Extract only the evidence and citation operations required by both views. Require an action selector and per-account selectors, assemble anchors with archive metadata, and sort by the contract. Preserve Deep Recall's existing output and failure semantics. Run the new test file, `test_deep_recall.py` and `test_deep_recall_limits.py` to green.

### 2. Shared access service and browser contract

Cover FR-001 and FR-006 in `tests/contracts/test_explorer_http.py`. Start with a failing test that sends the decision mode and expects the documented decision payload. Assert fixed errors for invalid mode, missing synthesis and rejected project, plus Host, Origin and authentication requirements for decision reads. Exercise ordinary Deep Recall with its original request and response.

Add the shared service method with the same scope validation as Deep Recall. Extend only the browser request schema and reuse existing authenticated dispatch. Run the HTTP suite and `tests/integration/test_deep_recall_mcp.py` to green.

### 3. Decision detail and exact-message navigation

Cover FR-001 through FR-006 in `tests/integration/test_explorer_browser.py`. Start with failing browser scenarios for the four labels and versions, documented rationale, equal and missing dates, both conflict accounts, exact message and stale source. Add empty and partial statuses, inert rendering, and a delayed response after changing scope or locking. Drive a mixed synthetic timeline through the real route and service.

Wire the form action to the existing Deep Recall POST in decision-history mode. Render the contract with semantic HTML and text nodes. Route event and conflict citations to `openConversation` using their original message anchors. Reuse abort and clearing behavior. Run the browser tests with a configured browser to green and validate the [quickstart](quickstart.md).

After the slices, run the focused verification commands and the full locked test suite. Reconcile every success criterion with observed results before review. The approved phase generates the detailed Spec Kit task list.
