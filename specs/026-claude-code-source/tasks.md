# Tasks: Claude Code session history

Input: specs/026-claude-code-source/{spec,plan,research,data-model}.md and contracts/source.md.
Tests are mandatory under constitution III: observe red before implementation.

## Phase 1: Setup

- [x] T001 Verify committed plan, approved gate, ignore files and available tooling in .claude/worktrees/27.

## Phase 2: Foundation

- [x] T002 Write failing context, sanitation and legacy-hash tests in tests/unit/test_source_context.py.
- [x] T003 Add optional `repository: Text | None = None` and `working_directory: Text | None = None` in src/engineering_memory/normalization/conversation.py and scan both in sanitization/pattern_sanitizer.py; keep canonical v1 unchanged.

## Phase 3: US1 — Debugging evidence (P1, MVP)

Independent test: parse a failure/investigation/fix, preserve each tool association and output, redact secrets.

- [x] T004 [US1] Write failing synthetic parser and source tests in tests/unit/test_claude_code_source.py with fixtures in tests/synthetic/claude_code.py.
- [x] T005 [US1] Implement ordered blocks, native identity/time, strict malformed-record refusal and resumable per-file iteration in src/engineering_memory/ingestion/claude_code/.
- [x] T006 [US1] Run CS-1–CS-7 against the source in tests/contracts/test_claude_code_source.py.

## Phase 4: US2 — Actual project (P1)

Independent test: explicit metadata beats conflicting prose and handles Windows/POSIX/URL context.

- [x] T007 [US2] Write failing metadata classification tests in tests/unit/test_source_context.py.
- [x] T008 [US2] Implement metadata classifier in src/engineering_memory/classification/metadata_classifier.py and compose it before aliases in cli/runtime.py.
- [x] T009 [US2] Write failing per-session provenance and CLI integration tests in tests/integration/test_claude_code_cli.py, then implement source selection and sanitized repository enrichment in cli/ and ingestion/pipeline.py.

## Phase 5: US3 — Incremental replay (P2)

Independent test: second import skips extraction, changed output updates identity, archive-only replay works.

- [x] T010 [US3] Write failing original replay and CLI skip/update/force/dry-run/isolation tests in tests/integration/test_claude_code_cli.py.
- [x] T011 [US3] Implement original-byte archive reader in src/engineering_memory/ingestion/claude_code/archive_source.py and register it in cli/runtime.py.
- [x] T012 [US3] Add opt-in live failure-root-cause recall, project/source scoping and sanitized access in tests/integration/test_claude_code_live.py.

## Phase 6: Polish

- [x] T013 Record ADR-010 in ARCHITECTURE.md and document commands/dialect in docs/claude-code.md; correct --from-archive usage in specs/026-claude-code-source/quickstart.md and contracts/source.md.
- [x] T014 Run Ruff, full pytest and live scenario; record outcomes in specs/026-claude-code-source/verification.md.
- [x] T015 Dispatch independent review, resolve findings, commit/push, open templated PR and move issue labels.

## Dependencies and execution strategy

T001 → T002 → T003. US1 follows foundation; US2 classifier tests can be authored independently
of US1 parser tests. US3 uses US1 adapter and US2 CLI composition. Finish with documentation,
verification and independent review. Within each story, test → observed failure → code → passing test.
MVP is US1; all three stories are required for the issue. Independent test-file authoring is a parallel
opportunity, but execution here is sequential. No production file has concurrent writers.
