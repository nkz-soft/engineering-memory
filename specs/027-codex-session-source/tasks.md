# Tasks: Codex session source

## Setup and foundations
- [x] T001 Review approved contracts and upstream format evidence in specs/027-codex-session-source/research.md.
- [x] T002 Create synthetic session builders in tests/synthetic/codex.py; validate parser failures before implementation.

## US1 — import and recall (P1)
Independent check: import, source-filtered recall, unchanged skip and original replay.
- [x] T003 [US1] Add shared source contract tests in tests/contracts/test_codex_source.py.
- [x] T004 [US1] Implement source and archive adapters in src/engineering_memory/ingestion/codex/.
- [x] T005 [US1] Add failing CLI/pipeline/replay tests in tests/integration/test_codex_cli.py then register in src/engineering_memory/cli/.

## US2 — evidence (P1)
Independent check: ordered request/output/fix chain and redaction.
- [x] T006 [US2] Add normalization and sanitizer cases in tests/unit/test_codex_source.py then implement parser.py.

## US3 — context and recovery (P2)
Independent check: valid/invalid/valid batch and per-session project tags.
- [x] T007 [US3] Test cwd priority, safe failures and context isolation in tests/integration/test_codex_cli.py and tests/unit/test_codex_source.py.

## Polish
- [x] T008 Document bounded dialect and ADR-011 in README.md and ARCHITECTURE.md.
- [x] T009 Add opt-in tests/integration/test_codex_live.py; run available checks and record actual results in specs/027-codex-session-source/quickstart.md.
- [x] T010 Review completed diff, fix findings and prepare the templated draft PR for publication.

## Dependencies and execution
T001 → T002/T003/T006 (tests first) → T004/parser → T005/T007 → T008/T009 → T010. US2 parser evidence is a prerequisite for US1 integration; US3 adds independent context/recovery checks. MVP is US1; full delivery includes all three. Test authoring in separate contract and unit files can proceed in parallel, as can final documentation and live-test preparation. Implementation proceeds sequentially here.

Live acceptance was subsequently verified by the operator: test_codex_live.py passed (1 passed in 4.16s). PR #69 was published and is ready for review; see quickstart.md for the verification record.
