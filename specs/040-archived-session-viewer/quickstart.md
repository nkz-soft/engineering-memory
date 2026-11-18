# Validation Guide: Archived Session Viewer

Run after approval and implementation from the feature worktree. These are planned commands, not claimed results.

## Prerequisites

Python 3.13, uv, project dev dependencies (uv sync --locked --group dev), Edge or Playwright Chromium. Use synthetic records only; no live Hindsight/private archive needed for these targeted suites.

## Checks

```powershell
uv run pytest tests/unit/test_access.py tests/contracts/test_explorer_http.py tests/integration/test_coding_agent_access.py
$env:ENGINEERING_MEMORY_BROWSER = 'msedge'
uv run pytest tests/integration/test_explorer_browser.py
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Browser scenarios must run, not all skip. Observe red before implementing each slice and record actual outcomes in the eventual PR.

## Scenarios

1. Both source sessions through real HTTP/shared-service/archive fixtures: dialogue, parallel calls, separate/orphan/absent/empty/error results, unknown tools, missing times and non-text markers remain ordered/readable.
2. Unified/apply_patch and recorded Edit old/new text are readable with exact raw access; malformed/unknown shapes fall back literally.
3. 10,000-line output starts collapsed, expands completely by keyboard and reveals a linked field automatically.
4. Message/tool targets at 0/49/50/100 open exactly; copy/reload/unlock/back/forward and next-page navigation remain correct.
5. Malformed selectors, wrong project, missing indexes and stale verified quote/time fail visibly. Plain links retain documented current-snapshot semantics.
6. Hostile shell/HTML/URLs/file references trigger no execution, dialogs, external requests or file reads. Preserve auth/Host/Origin/no-store and cancellation after lock/navigation.
7. Search, legacy prose, Deep Recall and decision-history citations still work.

See contracts/session-viewer.md and data-model.md for detailed expected behavior.
