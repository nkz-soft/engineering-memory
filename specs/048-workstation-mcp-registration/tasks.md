# Tasks: Workstation MCP Registration

**Input** [Specification](spec.md), [plan](plan.md), [contract](contracts/registration.md)

## Phase 1 - Setup and foundations

- [x] T001 Verify the worktree baseline against `specs/048-workstation-mcp-registration/plan.md`.
- [x] T002 Record verified vendor installation and profile layouts in `specs/048-workstation-mcp-registration/research.md`.

## Phase 2 - Connect installed clients (US1)

- [x] T003 [US1] Observe failing tests of each client subset and layout in `tests/unit/test_setup_client_discovery.py`.
- [x] T004 [US1] Implement current-user discovery and shared-profile grouping in `src/engineering_memory/setup_client_discovery.py`.

## Phase 3 - Inspect and preserve registrations (US2)

- [x] T005 [US2] Observe failing preservation, refusal and race tests in `tests/unit/test_setup_clients.py`.
- [x] T006 [US2] Implement snapshot-bound consent, guarded update and read-back in `src/engineering_memory/setup_clients.py`. Pin the TOML helper in `pyproject.toml` and `uv.lock`.

## Phase 4 - Verify local tools (US3)

- [x] T007 [US3] Observe failing bounded MCP tests in `tests/unit/test_setup_mcp_probe.py`.
- [x] T008 [US3] Implement isolated MCP verification in `src/engineering_memory/setup_mcp_probe.py`.
- [x] T009 [US1] Observe failing installer entry-point tests in `tests/unit/test_workstation_setup.py`.
- [x] T010 [US1] Connect the Windows installer and interactive terminal flow in `src/engineering_memory/cli/setup.py` and `packaging/workstation/windows.iss`.

## Phase 5 - CI and operator handoff

- [x] T011 Add a stable CI aggregate for both platform legs in `.github/workflows/ci.yml`.
- [ ] T012 Activate and verify the required status check in the GitHub main ruleset.
- [ ] T013 Publish review packages and checksums after installed smoke checks in `.github/workflows/release.yml`.
- [x] T014 Document setup and handoff in `docs/operations/workstation-install.md` and `specs/048-workstation-mcp-registration/quickstart.md`.

## Dependencies and execution order

Discover exact current-user targets, then implement their edit/read-back contract and the probe. Both installer paths consume those results. Begin each behavior with a failing test. The pull request records completion of the GitHub ruleset and artifact checks. The discovery CI job and release packaging can be exercised independently once their entry points work.
