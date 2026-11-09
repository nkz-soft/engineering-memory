# Tasks — Verify Reflect on the Accumulated Corpus

## Setup

- [x] T001 Verify the pinned reflection wire contract for `src/engineering_memory/memory/hindsight/store.py` and baseline test results.

## User Story 2 — Consumer synthesis

- [x] T002 [US2] Write failing wire and error tests in `tests/unit/test_hindsight_store.py`.
- [x] T003 [US2] Implement the reflection reader in `src/engineering_memory/memory/interface/store.py` and map the wire contract in `src/engineering_memory/memory/hindsight/`.
- [x] T004 [US2] Write failing MCP tests for scoped, archive-backed references in `tests/integration/test_access_mcp.py` and `tests/unit/test_access_reflect.py`.
- [x] T005 [US2] Register the read-only tool in `src/engineering_memory/access/server.py`, implement evidence validation in `src/engineering_memory/access/service.py`, and wire the reader in `src/engineering_memory/cli/runtime.py`.

## User Story 1 — Paired comparison

- [x] T006 [US1] Write failing paired-run and private-output tests in `tests/integration/test_reflect_evaluation.py`.
- [x] T007 [US1] Implement paired evaluation under `src/engineering_memory/evaluation/` and `src/engineering_memory/cli/evaluation.py`.
## Implementation PR verification

- [x] T010 Document the consumer routing and citation rule under `docs/operations/`.
- [x] T011 Verify offline and pinned-engine synthetic paths and record evidence in `specs/032-verify-reflect/verification.md`.
- [ ] T012 Complete independent review before marking the implementation PR ready.

## Final Phase 3 acceptance for #31

- [ ] T008 [US1] Freeze local cases and run the accumulated-corpus comparison using `specs/032-verify-reflect/quickstart.md`.
- [ ] T009 [US1] Publish reviewed aggregate results and limitations under `docs/operations/` and confirm or revise the consumer routing rule.

T003 follows T002. T005 follows T003 and T004. T007 follows T006 and can be verified against the stated MCP contract before T005 is integrated. T008 and T009 require the integrated tool and an authorized accumulated bank.
