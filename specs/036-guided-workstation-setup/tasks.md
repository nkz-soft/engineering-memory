# Tasks: Guided Workstation Setup

**Input** [specification](spec.md), [plan](plan.md) and [setup contract](contracts/setup.md)

## User Story 1 - Configure and start a workstation

- [x] T001 [P] [US1] Write failing profile tests in tests/unit/test_setup_profile.py for retention of private settings, coordinated endpoints and write recovery.
- [x] T002 [US1] Implement prompt validation and private profile persistence in src/engineering_memory/setup_profile.py.
- [x] T003 [P] [US1] Write failing CLI tests in tests/unit/test_workstation_setup.py for noninteractive invocation, provisioning order and failure isolation.
- [x] T004 [US1] Implement the installed setup command and lifecycle orchestration in src/engineering_memory/cli/setup.py and src/engineering_memory/cli/__init__.py.

## User Story 2 - Connect selected coding agents

- [x] T005 [P] [US2] Write failing tests in tests/unit/test_setup_clients.py for selected user-profile registration, retries and conflicts.
- [x] T006 [US2] Implement supported client discovery and registration in src/engineering_memory/setup_clients.py.

## User Story 3 - Select and import existing history

- [x] T007 [P] [US3] Write failing tests in tests/unit/test_setup_history.py for discovery, opt-out and import outcomes.
- [x] T008 [US3] Implement selected discovery and existing-importer dispatch in src/engineering_memory/setup_history.py.

## Packaging and verification

- [x] T009 Write failing handoff checks in tests/structure/test_workstation_release.py, then update packaging/workstation/windows.iss, packaging/workstation/smoke.py and docs/operations/workstation-install.md.
- [x] T010 Run the focused tests, full suite, lint and Windows bundle smoke checks. Record clean-workstation acceptance separately in the pull request.

T001, T003, T005 and T007 can begin independently. Complete each test-first pair before integration. Packaging follows the CLI entry point. Follow [clean-workstation validation](quickstart.md) with candidate artifacts on native Windows and Ubuntu.
