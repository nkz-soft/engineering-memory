# Tasks: Hindsight Memory Store

**Input**: spec.md, plan.md, research.md, data-model.md and contracts/memory-store.md.
**Workflow**: Tests must fail before corresponding implementation. No tasks marked done without evidence.

## Phase 1: Setup

- [x] T001 Confirm committed planning artifacts, branch and clean worktree in specs/015-hindsight-memory-store/plan.md.
- [x] T002 Check Docker context and required deployment inputs; record actual prerequisites in specs/015-hindsight-memory-store/verification.md.

## Phase 2: Foundational compatibility gate

- [ ] T003 Inspect pinned v1.1.0 OpenAPI/source and record exact retain/recall/operation schemas in specs/015-hindsight-memory-store/research.md.
- [ ] T004 Write and run explicit live compatibility tests for routes, UUID deduplication, async completion, strict tags, metadata and replace/append in tests/integration/test_hindsight_store.py.
- [ ] T005 Reconcile verified paths in ARCHITECTURE.md section 9; document any unsupported semantic requirement before proceeding.

Checkpoint: live compatibility evidence is a prerequisite to final transport design. Missing deployment inputs block T004; mocks cannot satisfy it.

## Phase 3: User Story 1 — Retain and recall (P1)

Independent test: retain a synthetic fact and recall typed provenance with strict project scope and limits.

- [ ] T006 [US1] Write failing HTTP mapping, provenance, empty recall, invalid limits and safe error tests in tests/unit/test_hindsight_store.py.
- [ ] T007 [US1] Implement ordered text/provenance encoding and validated response decoding in src/engineering_memory/memory/hindsight/serialization.py.
- [ ] T008 [US1] Implement settings/client ownership, timeouts, retain/recall and error translation in src/engineering_memory/memory/hindsight/store.py.
- [ ] T009 [US1] Bind existing MemoryStoreContract to the concrete adapter and a stateful wire fixture in tests/contracts/test_hindsight_store_passes_the_contract.py.

## Phase 4: User Story 2 — Replay and refresh (P1)

Independent test: replay uncertain delivery without repeated extraction, then replace changed content under the same document identity.

- [ ] T010 [US2] Write failing pending-key, async completion/deadline, force and A-to-B-to-A tests in tests/unit/test_hindsight_store.py.
- [ ] T011 [US2] Implement pending operation UUID lifecycle and bounded completion polling in src/engineering_memory/memory/hindsight/store.py.
- [ ] T012 [US2] Verify real operation reuse, completed extraction and replacement in tests/integration/test_hindsight_store.py.

## Phase 5: User Story 3 — Oversized conversations (P2)

Independent test: retain and refresh multipart text, recalling facts from beginning and end under the same identity.

- [ ] T013 [US3] Write failing Unicode, single oversized message, ordered chunks and replace/append tests in tests/unit/test_hindsight_store.py.
- [ ] T014 [US3] Implement lossless bounded UTF-8 splitting and one-request multipart payloads in src/engineering_memory/memory/hindsight/serialization.py.
- [ ] T015 [US3] Verify multipart refresh leaves no stale tail in tests/integration/test_hindsight_store.py.

## Phase 6: Cross-cutting verification and delivery

- [ ] T016 [P] Write failing direct/indirect import-violation tests, then enforce engine isolation in tests/structure/test_memory_implementation_boundary.py.
- [ ] T017 [P] Document exact offline and live commands and cross-process retry limits in specs/015-hindsight-memory-store/quickstart.md.
- [ ] T018 Run complete pytest, Ruff lint/format and pinned live checks; record red/green and completion evidence in specs/015-hindsight-memory-store/verification.md.
- [ ] T019 Request independent code review and resolve findings before delivery; record findings in specs/015-hindsight-memory-store/verification.md.
- [ ] T020 Commit/push, compose .github/pull_request_template.md with actual evidence, open PR closing #16 and move issue to in-review.

## Dependencies and execution order

Setup → compatibility gate → US1 → US2 → US3 → final verification/review/PR. Within each story tests precede implementation. T016 and T017 can proceed independently of each other once implementation shape is established. US1 MVP validation cannot waive US2/US3 acceptance for issue completion.

## Parallel examples

US1: recall-fixture assertions and provenance fixtures may be designed independently, but edits to test_hindsight_store.py are serialized. US2: live operation evidence can be collected independently of local deadline tests once T004 succeeds. US3: live refresh observation can run independently of Unicode unit cases. T016 and T017 have disjoint files. No parallel agents are required by this task list.

## Implementation strategy

Validate the pinned contract first. Implement the smallest retain/recall slice with tests, then replay, then multipart delivery. Each story is validated through its own synthetic scenario. Never replace required live evidence with a passing mocked fixture.
