# Tasks: Reviewed Project Playbooks

## Setup

- [x] T001 Confirm the worktree, approved design, and requirements checklist in `specs/044-project-playbooks/`.

## US1 — Review and approve a draft

- [x] T002 [US1] Add failing writer, transaction and CLI tests in `tests/unit/test_playbook_store.py` and `tests/unit/test_playbook_cli.py`.
- [x] T003 [US1] Implement validated models, reader/writer protocols, SQLite catalog and operator service in `src/engineering_memory/playbooks/`.
- [x] T004 [US1] Wire stage, review and approve through `src/engineering_memory/cli/` and rerun the focused tests.

## US2 — Discover and open an approved playbook

- [x] T005 [US2] Add failing access, stdio, HTTP and browser checks in `tests/unit/test_access_playbooks.py`, `tests/integration/test_access_mcp.py`, `tests/contracts/test_explorer_http.py` and `tests/integration/test_explorer_browser.py`.
- [x] T006 [US2] Share approved reads and guarded evidence through `src/engineering_memory/access/`, then wire MCP and the authenticated explorer in `src/engineering_memory/api/`.

## US3 — Preserve approved history

- [x] T007 [US3] Verify two publications, draft isolation, exact project scope, immutable version history and stale source handling across store and transports.

## Verification

- [x] T008 Document use and backup in `docs/operations/local-memory-explorer.md` and `docs/operations/coding-agent-memory.md`.
- [ ] T009 Run the suite and review the branch before opening the PR.

US1 establishes the writer and durable catalog. US2 uses the catalog reader. US3 exercises the same boundaries across two versions.
