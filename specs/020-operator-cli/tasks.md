# Tasks: Operator CLI

## Setup
- [x] T001 Read design and validate existing dependencies/configuration in specs/020-operator-cli/plan.md.

## Foundation
- [x] T002 Write failing enumeration/readonly contracts in tests/contracts/state.py and tests/unit/test_operator_cli.py (read-only enforcement through status).
- [x] T003 Extend ImportState and SQLite/fake enumeration in src/engineering_memory/ingestion/state.py, src/engineering_memory/ingestion/sqlite_state.py and tests/fakes/state.py.

## US1: Provision (P1)
Independent test: invoke provision with fake provisioning service, text/JSON and safe failures.
- [x] T004 [US1] Write failing structured output/error tests in tests/unit/test_operator_cli.py.
- [x] T005 [US1] Implement result rendering and provision JSON in src/engineering_memory/cli/__init__.py and results.py.

## US2: Import/replay (P1)
Independent test: real synthetic export/archive/state with fake memory; repeat/force/mixed failure.
- [x] T006 [US2] Write failing command integration tests in tests/integration/test_operator_cli.py.
- [x] T007 [US2] Compose existing adapters and implement import in src/engineering_memory/cli/runtime.py and __init__.py.

## US3: Status/scripting (P2)
Independent test: inspect local state offline without mutation, including missing/corrupt state.
- [x] T008 [US3] Write failing offline/status safety tests in tests/unit/test_operator_cli.py.
- [x] T009 [US3] Add narrow local settings and status rendering in src/engineering_memory/settings.py and cli/runtime.py.

## Polish
- [x] T010 Add opt-in live command workflow in tests/integration/test_operator_cli.py; run fixture/live validation per specs/020-operator-cli/quickstart.md.
- [x] T011 Document commands/flags and close deferred surface decision in README.md and ARCHITECTURE.md.
- [x] T012 Run full tests/lint and review finished diff; record verification in specs/020-operator-cli/verification.md, then publish PR.

## Dependencies and execution
Foundation precedes status; US1/US2 share rendering. Execute tests before implementation in each slice. US1 tests and enumeration tests can be authored independently; US2 integration and US3 offline tests can run independently once composition exists. Deliver provision compatibility first, then import/replay and offline status. No tasks require new dependencies or database migrations.
