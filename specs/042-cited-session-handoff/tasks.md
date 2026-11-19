# Tasks — Cited session handoff

## Setup

- [x] T001 Resolve the active feature and verify the committed requirements checklist in `specs/042-cited-session-handoff/checklists/requirements.md`.

## Foundation and story 1 — CLI handoff (P1)

- [x] T002 [US1] Write and observe failing shared-access tests for session scope, sanitized evidence, archive coverage, selectors and Markdown in `tests/unit/test_session_handoff.py`.
- [x] T003 [US1] Implement selection, evidence, structured synthesis validation and rendering in `src/engineering_memory/access/handoff.py` and `src/engineering_memory/access/service.py`.
- [x] T004 [US1] Write and observe failing adapter and CLI tests in `tests/unit/test_session_handoff_cli.py`. Extend the existing synthesis transport and wire the command in `src/engineering_memory/access/synthesis.py`, `src/engineering_memory/cli/runtime.py`, `src/engineering_memory/cli/__init__.py` and `src/engineering_memory/settings.py`.

**Independent test** — Import a synthetic Claude Code record and invoke `session-handoff` without a viewer. Check Markdown, recorded and unknown outcomes, selected-session anchors and error output.

## Story 2 — Viewer handoff (P2)

- [x] T005 [US2] Write and observe failing HTTP and browser tests in `tests/contracts/test_explorer_http.py` and `tests/integration/test_explorer_browser.py`.
- [x] T006 [US2] Add the authenticated route and session-only clipboard flow in `src/engineering_memory/api/explorer.py` and `src/engineering_memory/api/explorer_assets/explorer.js`.

**Independent test** — Open a synthetic session in the unlocked viewer. Generate and copy Markdown, open an anchor and verify denial and stale-result handling.

## Verification

- [x] T007 Update `docs/operations/local-memory-explorer.md` and exercise the automated scenarios in `quickstart.md`.
- [x] T008 Verify a manual paste into a fresh Codex session and compare with the synthetic source.
- [x] T009 Run repository checks and obtain independent code review before opening the PR.

## Acceptance evidence

A fresh Codex context received only the generated synthetic Markdown. It recovered the relay investigation, port 8123 decision, recorded change to relay.conf, unknown proposed.conf edit, failed and successful check runs in order, and the open documentation question. It cited the corresponding message positions. The standalone Codex CLI returned model_not_found; the isolated Codex context was used for the recipient check.

## Dependencies and delivery

T002 → T003 → T004 provides the CLI release slice. T005 can be prepared alongside CLI tests once the access operation is fixed. T006 needs T003 and T005. Complete both slices before final validation.
