# Tasks: Hindsight retries

Input: approved spec.md, plan.md, research.md, data-model.md and contracts/. Approval: user reran /issue-to-pr 20 after planning gate.

## Phase 1: Setup
- [x] T001 Verify dependencies and ignore rules in pyproject.toml and .gitignore; read design artifacts.

## Phase 2: Foundation
- [x] T002 Write failing dependency assertion in tests/structure/test_packaging.py; add Tenacity to pyproject.toml and uv.lock.

## Phase 3: US1 — Recover without duplicate extraction
Independent test: transient retain/poll/recall failures recover with unchanged payloads.
- [x] T003 [US1] Write failing transport recovery and identity tests in tests/unit/test_hindsight_retry.py.
- [x] T004 [US1] Implement private bounded policy in src/engineering_memory/memory/hindsight/retry.py and integrate src/engineering_memory/memory/hindsight/store.py.

## Phase 4: US2 — Permanent failures and limits
Independent test: single attempt on rejection; bounded attempts/deadline on transient failures.
- [x] T005 [US2] Write failure classification, deadline, policy validation and exhaustion tests in tests/unit/test_hindsight_retry.py.
- [x] T006 [US2] Implement policy validation and safe exhaustion in src/engineering_memory/memory/hindsight/retry.py; preserve pending replay in store.py and update tests/unit/test_hindsight_store.py.

## Phase 5: US3 — Safe diagnostics
Independent test: structured attempts and final outcomes exclude synthetic canaries.
- [x] T007 [US3] Write safe structured-event tests in tests/unit/test_hindsight_retry.py.
- [x] T008 [US3] Implement allowlisted events in src/engineering_memory/memory/hindsight/retry.py and correlation in store.py.

## Phase 6: Polish
- [x] T009 Run specs/019-hindsight-retry/quickstart.md checks and record results in verification.md.
- [x] T010 Request independent code review, fix findings and update specs/019-hindsight-retry/plan.md status.

## Dependencies and strategy
T001 → T002 → US1 → US2 → US3 → verification/review. Tests precede implementation, observing red then green per increment. Recovery is the MVP; all stories ship together. No parallel edits to shared store/test files. Independent contract and structure verification may run in parallel after implementation. No extension hooks installed.
