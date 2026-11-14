# Tasks: Deep Recall

## Cross-session explanations

- [x] T001 [US1] Define the timeline and bounds with failing cases in tests/unit/test_deep_recall.py.
- [x] T002 [US1] Implement the shared access coordinator in src/engineering_memory/access/deep_recall.py and src/engineering_memory/access/service.py.
- [x] T003 [US1] Test and wire CLI, MCP, and the opt-in synthesis adapter in tests/unit/test_deep_recall_cli.py, tests/integration/test_deep_recall_mcp.py, and src/engineering_memory/access/synthesis.py.

## Evidence gaps and scope

- [x] T004 [US2] Verify insufficient evidence, truncation, and rejected quotations in tests/unit/test_deep_recall.py.
- [x] T005 [US3] Verify foreign hits and mismatched archives stay out of synthesis in tests/unit/test_deep_recall.py.

## Release checks

- [x] T006 Document configuration and interpretation in docs/operations/deep-recall.md.
- [x] T007 Run regression checks and record results in specs/034-deep-recall/verification.md.
