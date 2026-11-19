# Verification: Evidence-backed session neighborhood

**Environment** — Windows x64, 24 logical processors, Python 3.13, Microsoft Edge 157. Browser checks used Playwright from the local development environment.

## Acceptance

- Synthetic native Codex records were parsed and stored in the local archive. They contained a confirmed file edit, confirmed commit, qualified PR reference and explicit continuation. The browser selected all four and focused the exact supporting message or tool result. Tests also covered Claude Code checkout inference and the omission of cross-project and cross-repository path collisions.
- A prepared index of 50,000 sessions with 2,500 edits to one file rendered the first 30 direct edges in about 0.09 seconds from keyboard activation. The browser identified truncation and returned the same selection and order on a second request. SQLite query plans showed an indexed search in each direction with a limit of 31 and no temporary sort.
- Review regressions exercised directory rejection before and during refresh, retained generation rollback, mixed workspaces, legacy snapshots with incomplete checkout context, private index creation, stale and absent viewer fields, long Unicode selectors, and bounded evidence excerpts.
- Current imports retain operation cwd in recognized sanitized tool request envelopes. Historical snapshots without enough checkout context omit ambiguous relative edits and commits until the originals are replayed.

## Commands

- `pytest -q` in the locked project environment. 2,464 passed and 91 skipped with optional live service and browser runs disabled.
- Python focused regression run with `pytest -q` on the neighborhood, explorer HTTP and CLI, both source parsers and local archive suites. 181 passed and 2 skipped.
- `pytest -qs tests/integration/test_evidence_neighborhood.py tests/integration/test_explorer_browser.py -k "neighborhood or guarded"` with `ENGINEERING_MEMORY_BROWSER=msedge`. 8 passed and 35 deselected.
- `ruff check src tests`, `ruff format --check src tests`, `node --check src/engineering_memory/api/explorer_assets/explorer.js` and `git diff --check`. All passed.
