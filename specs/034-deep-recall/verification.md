# Deep Recall verification

```text
.venv/Scripts/python -m pytest -q --tb=short
2259 passed, 44 skipped

.venv/Scripts/ruff check .
All checks passed

.venv/Scripts/ruff format --check .
601 files already formatted

.venv/Scripts/engineering-memory.exe deep-recall --help
Shows the required query and --project, with optional --json
```

The cross-source test imports synthetic native Claude Code and Codex exports, uses the actual normalized archive and MCP stdio, and verifies both citations through conversation paging. Retrieval and synthesis use deterministic test adapters. The HTTP adapter is exercised with mocked responses, including timeout, redirects and oversized output. Live provider behavior was not verified.
