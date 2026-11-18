# Verification: Archived Session Viewer

## Workflow

Human resumed Phase 2 with `/issue-to-pr 86` after published specification/plan.
Implementation stayed in `.claude/worktrees/86` on `040-archived-session-viewer`.
No extension hooks are configured. No new transport, schema or dependency.

## Test-first evidence

- Baseline: existing access/HTTP/browser checks, 69 passed.
- Recorded envelope scenarios: four expected assertion failures before presentation implementation, then four passed.
- Fragment selectors: missing exact-target behavior failed before navigation implementation. Disclosure and malformed-target regressions cover long output and fail-closed parsing.
- Review regression: long serialized output/non-text markers failed first, then decoding-before-disclosure and marker presentation were corrected.
- Same-fragment reactivation: target focus assertion failed first; explicit resolution on same-fragment click corrected it.
- Source-specific, boundary-position, refresh/unlock, back/forward, absent/empty/error, malformed selectors, invalid citation, keyboard disclosure and inert markup scenarios use synthetic content.

## Commands and results

- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: 683 files already formatted.
- `uv run pytest -q --tb=short`: 2356 passed, 80 skipped. Skips include opt-in browser/live integration conditions; real browser run is recorded separately below.

## Review

Independent reviewer reported three issues (decode long envelopes before disclosure, show non-text markers, collapse prose) and then a same-link reactivation issue. All corrected. Final review: no remaining important findings. Quote/time verification and aborted-request checks retained.

## Limits

Saved links select the current archived snapshot; they do not retain old revisions. Per-launch origin/key is not stable hosting. Disclosure limits visual output rather than archive I/O or response bytes. Recorded patches are text evidence, never applied. No live Hindsight/source services or private archive used for validation.

- Real browser: $env:ENGINEERING_MEMORY_BROWSER='msedge'; uv run --with playwright pytest tests/integration/test_explorer_browser.py -q --tb=short: 32 passed (no skips).
