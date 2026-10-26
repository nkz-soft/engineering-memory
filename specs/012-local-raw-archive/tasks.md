# Tasks: Local Raw Archive

**Input**: `specs/012-local-raw-archive/` design artifacts.
**Tests**: Required; observe red before implementation for each behavior group.

## Phase 1: Setup

- [x] T001 Verify committed plan, constitution, checklist and ignore files in specs/012-local-raw-archive/ and .gitignore.
- [x] T002 Establish runnable Python 3.13 environment from pyproject.toml and baseline tests.

## Phase 2: Foundation

- [x] T003 Write failing enumeration contracts (empty, unique replacement, source filter, repeatable membership, declared failure) in tests/contracts/archive.py.
- [x] T004 Add iter_document_ids to src/engineering_memory/archive/interface.py and tests/fakes/archive.py; verify shared fake contracts.

## Phase 3: US1 — Durable source of truth (P1 MVP)

Independent test: reopen local storage and recover both exact forms; inject failures and observe complete pairs only.

- [x] T005 [US1] Write failing local contract adapter and persistence tests in tests/contracts/test_local_archive_passes_the_contract.py and tests/unit/test_local_archive.py.
- [x] T006 [US1] Implement version-1 envelope in src/engineering_memory/archive/local.py: format_version is integer literal 1, unknown fields forbidden, exact nonempty media type, strict base64, full enriched identity and content hash validation.
- [x] T007 [US1] Write failing publication, filesystem failure, corrupt/future format, binary payload, hostile-ID, symlink and concurrent-reader tests in tests/unit/test_local_archive.py.
- [x] T008 [US1] Implement atomic paired publication, file and supported directory synchronization, resumable enumeration and safe boundary errors in src/engineering_memory/archive/local.py.

## Phase 4: US2 — Original-based replay (P1)

Independent test: remove synthetic export and replay all valid conversations through current processing rules.

- [x] T009 [P] [US2] Write failing original-based source and per-document continuation tests in tests/unit/test_archive_replay_source.py.
- [x] T010 [P] [US2] Write deleted-export integration acceptance with real parser/sanitizer/classifier and fresh fake state in tests/integration/test_archive_replay.py.
- [x] T011 [US2] Implement ChatGPTArchiveSource with fresh source-filtered enumeration, identity verification and safe resumable parsing in src/engineering_memory/ingestion/chatgpt/archive_source.py.

## Phase 5: US3 — Replaceable storage (P2)

Independent test: both implementations satisfy the same suite, broken enumeration is caught, interface imports stay isolated.

- [x] T012 [US3] Exercise both implementations and prove enumeration guards reject a broken archive in tests/contracts/test_suites_bite.py; preserve tests/structure boundary checks.

## Phase 6: Polish and review

- [x] T013 [P] Document settled layout, replay and durability limits in ARCHITECTURE.md and specs/012-local-raw-archive/quickstart.md.
- [x] T014 Run focused and full pytest suites, Ruff lint/format, diff checks; record evidence in specs/012-local-raw-archive/verification.md.
- [x] T015 Request independent code review, resolve important findings, and record review in specs/012-local-raw-archive/verification.md.
- [ ] T016 Commit/push, open PR from .github/pull_request_template.md, attach PR, and move issue #13 to in-review.

## Dependencies and execution

Setup → Foundation → US1 → US2 → US3 → verification/review → PR.
T009 and T010 are independent test files and may be prepared together; T013 is independent documentation work after design settles. Each implementation follows its failing tests. US3 uses shared contracts established in Foundation and local storage from US1. MVP checkpoint is US1; full delivery also requires replay and replacement validation. No deployment or production orchestration is included.
