# Validation Guide — Source-Backed Decision History

Use synthetic archives with an explicitly adopted configuration A in project `sample-project`, a documented revision, and a later session explicitly replacing A with B for a documented reason. Include a proposal in an earlier message, an undated action, two equal-time actions, a disputed date, an unresolved disagreement and a second project with a matching decision topic.

## Automated checks after implementation

```sh
uv run --locked pytest -q tests/unit/test_decision_history.py tests/unit/test_deep_recall.py tests/unit/test_deep_recall_limits.py tests/contracts/test_explorer_http.py
uv run --locked pytest -q tests/integration/test_deep_recall_mcp.py
uv run --locked ruff check .
```

Run the browser suite using the setup in the [local explorer validation guide](../038-local-memory-explorer/quickstart.md):

```sh
uv run --locked --with playwright pytest -q tests/integration/test_explorer_browser.py tests/integration/test_explorer_launch.py
```

Set `ENGINEERING_MEMORY_BROWSER` to the installed `chromium` or `msedge` target before the browser run. Verify the decision browser scenarios execute. The synthetic browser fixture should run through the real explorer route and service, swapping I/O at existing memory, archive and synthesis boundaries.

## Operator acceptance

1. Configure the existing [Deep Recall synthesis endpoint](../../docs/operations/deep-recall.md), launch `uv run --locked engineering-memory explore` and unlock the browser.
2. Enter the fixture project and topic and select **Decision history**. Check all four lifecycle labels, both versions, the documented rationale and chronological order. Verify the foreign project is absent.
3. Inspect visible uncertainty and the competing accounts. Open each event source and each competing account's evidence. Confirm the correct message is highlighted and that an unavailable or changed source produces a clear error.
4. Exercise empty, partial and invalid synthesis fixtures. Repeat with a delayed response, then change project or lock the explorer. Confirm that the pending response cannot restore cleared history.
