# Tasks: Live Hindsight Contract

## Setup
- [x] T001 Inspect pinned engine extraction/schema and temporal/tag semantics; record evidence in specs/017-live-hindsight-contract/research.md.

## Foundation
- [x] T002 Write failing fixture protocol/counter tests in tests/unit/test_contract_llm.py.
- [x] T003 Implement fail-closed extraction service in tests/integration/hindsight_contract/llm.py and test-only deploy/hindsight/compose.contract.yaml.

## US1 — Identity and retry (P1)
- [x] T004 [US1] Write and run failing replacement/replay assertions in tests/integration/test_live_hindsight_contract.py.
- [x] T005 [US1] Complete scratch-bank fixtures, extraction barrier/counter checks and negative controls in tests/integration/hindsight_contract/.

## US2 — Retrieval scope and time (P1)
- [x] T006 [US2] Write tag truth-table, historical-time and untouched-bank tests in tests/integration/test_live_hindsight_contract.py.
- [x] T007 [US2] Validate all assertions against the pinned live engine and record literal modes and temporal behavior in ARCHITECTURE.md.

## US3 — Automatic gate (P2)
- [x] T008 [US3] Write failing CI/no-skip runner checks in tests/unit/test_contract_runner.py and tests/structure/test_ci_workflow.py.
- [x] T009 [US3] Implement bounded isolated runner in deploy/hindsight/contract.py and dedicated job in .github/workflows/ci.yml.

## Verification and delivery
- [x] T010 Run offline tests, lint/format, negative controls and two live runs; update specs/017-live-hindsight-contract/quickstart.md and verification.md.
- [x] T011 Request independent review, resolve findings, commit/push and open PR using .github/pull_request_template.md.

## Dependencies and strategy

T001 -> T002 -> T003 -> US1 -> US2 -> US3 -> verification/review. Each story has an independent pytest selection. US1 is the MVP but all three stories are required for issue completion. Negative-control tests for separate families can run in parallel after shared fixtures exist; live engine calls remain sequential to keep extraction counters unambiguous.
