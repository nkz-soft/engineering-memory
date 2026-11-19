# Quickstart: Validate the evidence neighborhood

Run these checks after implementation, using synthesized source records and a disposable data directory.

1. Run `uv sync --locked`. Configure the existing local archive/explorer as described in the [operator guide](../../docs/operations/local-memory-explorer.md). Import synthetic Codex and Claude Code histories with a confirmed edit, a failed edit, a confirmed commit, a qualified PR reference and an explicit continuation. Include equal relative paths in separate projects and repositories and a stale/unavailable source case.
2. Run `uv run engineering-memory rebuild-neighborhood` and launch the explorer using the [operator guide](../../docs/operations/local-memory-explorer.md). Open the source session and select each relation using the keyboard. Confirm all four supported types, exact viewer fields, and the omission of failed and ambiguous records.
3. Open the repeated relative path separately in each project/repository. Check that only matching sessions appear. Modify a fixture after indexing and verify that its stale evidence is unavailable. Refresh and check the updated neighborhood.
4. Run the focused suites with `uv run pytest tests/unit/test_neighborhood_evidence.py tests/contracts/test_explorer_http.py tests/integration/test_explorer_browser.py` and the new SQLite adapter tests. Capture the query plan and browser timing on the synthetic 50,000-session fixture with at least 2,000 edits to one file. Confirm the graph shows at most 30 edges and reports truncation. Repeat with an unchanged index to verify deterministic results. Record test workstation details with the timing.
5. Verify that locking, switching roots during a request, a missing index and an interrupted refresh preserve existing explorer behavior.
