# Tasks: Bank Provisioning

## Setup and foundations
- [x] T001 Inspect pinned API and existing settings; record evidence in research.md.
- [x] T002 Write failing mission and config transport tests in tests/unit/test_bank_provisioning.py.

## User Story 1 — prepare the bank (P1)
- [x] T003 [US1] Implement bounded config provisioning and mission resource in src/engineering_memory/memory/hindsight/provision.py and mission.txt.
- [x] T004 [US1] Write failing CLI success/failure tests in tests/unit/test_provision_cli.py; wire src/engineering_memory/cli/__init__.py.
- [x] T005 [US1] Add opt-in scratch-bank tests in tests/integration/test_bank_provisioning.py.

## User Story 2 — evolve priorities (P2)
- [x] T006 [US2] Test repeat, replacement and preservation in tests/unit/test_bank_provisioning.py and tests/integration/test_bank_provisioning.py.
- [x] T007 [US2] Document policy evolution in docs/development/local-hindsight.md.

## Verification
- [x] T008 Run full tests/lint/format; record results and live prerequisites in verification.md.
- [x] T009 Request independent code review, fix findings, and open PR using .github/pull_request_template.md.

## Dependencies and execution
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009.
US1 is the MVP; US2 independently verifies existing-bank policy changes. Unit and CLI tests can be authored independently, but each implementation follows an observed failure. No parallel implementation is needed for this small change. No extension hooks configured. Requirements checklist: 16/16 PASS.


Live runtime acceptance remains pending as recorded in verification.md; T008 records the attempted test and does not claim live success. T009 produces a draft PR for this reason.

