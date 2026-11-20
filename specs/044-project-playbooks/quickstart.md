# Playbook Acceptance Run

Run after implementation. Use a temporary local archive, configure `ENGINEERING_MEMORY_ARCHIVE_ROOT` to its root and import synthetic conversations with the normal importer. Prepare same-project examples A and B and a third example assigned to another classified project. Use their archive document IDs in the fixture files.

1. Create `v1.json` with `{"title":"Release checks","steps":["Run tests","Confirm the release notes"],"examples":["DOCUMENT_A"]}`. Stage and review it with the CLI commands in [the contract](contracts/playbooks.md). Confirm that the CLI shows the ordered steps, example and revision. Search for a distinct draft-only phrase through ordinary search and verify it is absent. List playbooks for the project over MCP and in the explorer. Both lists are empty.
2. Approve the reviewed token. Over stdio call `list_project_playbooks`, then `get_project_playbook` and guarded `get_conversation` using the example's project and snapshot. In `engineering-memory explore`, select the same project, open the playbook and follow the example link. Verify both surfaces show the approved steps and the sanitized transcript. A request in the other project returns no playbook.
3. Stage an update with reordered steps and example B. Confirm v1 remains the default. Replace that pending draft, attempt approval using its old token and verify the operation fails without a new version. Review and approve the current token. Confirm v2 becomes the default and both readers can open v1 with A and v2 with B.
4. Try staging with the other project's document ID. Verify it is rejected. For another pending draft, change its source in the test archive before approval. Verify the approval is rejected. After an approved example changes, verify its recorded reference remains visible, and guarded navigation reports unavailable evidence.
5. Run the targeted test suite and check each acceptance outcome above.

```sh
uv run pytest tests/unit/test_playbook_store.py tests/unit/test_playbook_cli.py tests/unit/test_access_playbooks.py tests/integration/test_access_mcp.py tests/integration/test_deep_recall_mcp.py tests/contracts/test_explorer_http.py tests/integration/test_explorer_browser.py
```
