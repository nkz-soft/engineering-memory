# Tasks: Claude chat history source

## Phase 1: Setup

- [x] T001 Verify committed plan, constitution, ignored data/worktrees and source contract in specs/025-claude-chat-source/plan.md.

## Phase 2: Foundation

- [x] T002 Add synthetic Claude record builders in tests/synthetic/claude_export.py; native id nonempty, required timezone-bearing created_at, optional title/update/message times, ordered required chat_messages.

## Phase 3: US1 — Import (P1, MVP)

Independent check: parser, packaging and all CS rules against synthetic exports.

- [x] T003 [US1] Write and observe failing parser/packaging/contract tests in tests/unit/test_claude_source.py and tests/contracts/test_claude_source.py.
- [x] T004 [US1] Implement parser and resumable export reader in src/engineering_memory/ingestion/claude_chat/; preserve roles, text-block precedence/order, original bytes and safe errors.
- [x] T005 [US1] Write failing source-selection tests in tests/integration/test_claude_cli.py, then register --source in src/engineering_memory/cli/__init__.py and runtime.py with ChatGPT default and early usage refusal.

## Phase 4: US2 — Mixed recall (P1)

Independent check: shared pipeline imports colliding native ids, sanitizes secrets, preserves tags and supports source-filtered recall/open.

- [x] T006 [US2] Add mixed-source pipeline/access tests in tests/integration/test_claude_pipeline.py and opt-in live recall in tests/integration/test_claude_live.py; observe fail before relevant implementation.
- [x] T007 [US2] Verify existing shared stages satisfy tests without changes in src/engineering_memory/ingestion/claude_chat/.

## Phase 5: US3 — Preview/replay (P2)

Independent check: preview makes zero writes/calls; archive-only forced replay reparses originals.

- [x] T008 [US3] Write failing replay, idempotency, force and dry-run tests in tests/integration/test_claude_pipeline.py and tests/integration/test_claude_cli.py.
- [x] T009 [US3] Implement ClaudeChatArchiveSource in src/engineering_memory/ingestion/claude_chat/archive_source.py and register archive selection in src/engineering_memory/cli/runtime.py.

## Phase 6: Polish

- [x] T010 Record claude_chat in .specify/memory/constitution.md (patch 1.3.1), append ADR-009 to ARCHITECTURE.md and document source selector/export limitations in README.md and specs/025-claude-chat-source/quickstart.md.
- [x] T011 Run lint, format, full pytest, live check if configured; record results and review fixes in specs/025-claude-chat-source/verification.md.
- [ ] T012 Commit, push, open PR using .github/pull_request_template.md and move issue #26 to in-review.

## Dependencies and execution

T001 -> T002 -> T003 -> T004 -> T005. T006 and T008 test design can run independently
once fixtures exist; implementation and verification run sequentially. US2/US3 use US1's parser.
MVP is US1, then mixed recall, then preview/replay; all are required before PR completion.
Parallel opportunities: independent contract and parser test files, or live and offline integration
scenarios. Each implementation change follows an observed failing test; no shared policy changes.

