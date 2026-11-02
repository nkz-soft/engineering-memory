# Tasks: Hermes memory access

Input: spec.md, plan.md, research.md, data-model.md, contracts/tools.md, quickstart.md.
Test-first is mandatory under Principle III; observe failures before implementation.

## Phase 1: Setup and foundation
- [x] T001 Resolve design artifacts and validate completed specification checklist.
- [x] T002 Add official MCP SDK to pyproject.toml/uv.lock and synchronize environment.

## Phase 2: User Story 1 — search imported history (P1)
- [x] T003 [US1] Write failing tests for search/filter/provenance/limits/errors in tests/unit/test_access.py.
- [x] T004 [US1] Implement interface-injected search and safe request validation in src/engineering_memory/access/service.py.

## Phase 3: User Story 2 — read original context (P2)
- [x] T005 [US2] Write failing paging, identity, normalized-only and failure tests in tests/unit/test_access.py.
- [x] T006 [US2] Implement conversation paging in src/engineering_memory/access/service.py.

## Phase 4: User Story 3 — reproduce consumer connection (P2)
- [x] T007 [US3] Write failing protocol tests in tests/integration/test_access_mcp.py and settings/CLI tests in tests/unit/test_access_cli.py.
- [x] T008 [US3] Implement two-tool stdio registration in src/engineering_memory/access/server.py.
- [x] T009 [US3] Add access settings in src/engineering_memory/settings.py and serve composition in src/engineering_memory/cli/.
- [x] T010 [US3] Document configuration, filters, troubleshooting and acceptance in docs/operations/hermes-memory.md; link README.md.

## Phase 5: Verification and review
- [x] T011 Run regression/lint/format checks and SDK subprocess integration; record commands and outcomes.
- [x] T012 Exercise live import-to-MCP retrieval and scoped distractor against isolated deployment.
- [ ] T013 Demonstrate fresh Hermes conversation and reproducible second setup; record safe evidence.
- [x] T014 Request code review, fix findings, commit/push and open PR using repository template.

## Dependencies and execution
T001 → T002 → T003 → T004. T005 → T006 follows the same validation model;
T007 precedes T008/T009. T010 follows public tool/CLI completion. T011–T014 follow
all stories. US1 and US2 are separately testable via injected boundaries; US3 composes
both. Parallel opportunities: service tests and CLI tests touch independent files;
consumer docs can be reviewed while regression checks run. Execute sequentially here.

## Strategy
Deliver validated read services first, then transport and launch, then documentation
and live evidence. Unavailable external prerequisites remain unchecked with an explicit
reason; automated doubles never substitute for live consumer acceptance.
