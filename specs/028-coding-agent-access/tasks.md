# Tasks: Shared memory for coding agents

**Input**: spec.md, plan.md, research.md, data-model.md and contracts/
**Tests**: Test-first for executable changes; existing access behavior receives regression coverage.

## Phase 1: Setup

- [x] T001 Review approved design, constitution and ignore files; record prerequisites in specs/028-coding-agent-access/verification.md.

## Phase 2: Foundation

- [x] T002 Add a failing gate test for omitted cross-agent regression in tests/unit/test_e2e_runner.py, then extend deploy/hindsight/e2e.py to require it.

## Phase 3: US1 — ChatGPT to Claude Code (P1, MVP)

Independent test: fresh Claude Code recalls an imported decision and opens normalized context.

- [x] T003 [US1] Add synthetic ChatGPT/competing-project import-to-stdio regression in tests/integration/test_coding_agent_access.py.
- [x] T004 [US1] Document Claude Code registration, environment and scoped recall in docs/operations/coding-agent-memory.md.
- [x] T005 [US1] Execute real Claude Code acceptance under #71 and record the positive Orchard and Cypress results in specs/028-coding-agent-access/verification.md.

## Phase 4: US2 — Claude Code to Codex (P1)

Independent test: import a completed refinement and retrieve it in fresh Codex.

- [x] T006 [US2] Extend tests/integration/test_coding_agent_access.py with before/after import visibility, identity, time, negative filters, sanitized paging and unchanged-import skipping.
- [x] T007 [US2] Document Codex config/env_vars and import-mediated refinement workflow in docs/operations/coding-agent-memory.md.
- [ ] T008 [US2] Deferred to #71 (T014): execute actual session refinement/import/Codex acceptance and record evidence or blocker in specs/028-coding-agent-access/verification.md.

## Phase 5: US3 — Reproducibility (P2)

Independent test: register clients from the guide and distinguish backend evidence from consumer acceptance.

- [x] T009 [US3] Link operations guide from README.md, docs/claude-code.md and docs/codex.md.
- [x] T010 [US3] Validate config syntax with installed clients using isolated temporary settings; record versions and results in specs/028-coding-agent-access/verification.md.

## Phase 6: Verification and review

- [x] T011 Run regression, full pytest, Ruff and isolated live gate; record actual results in specs/028-coding-agent-access/verification.md.
- [x] T012 Request independent review, resolve findings, and record outcome in specs/028-coding-agent-access/verification.md.
- [x] T013 Update specs/028-coding-agent-access/quickstart.md and tasks.md, push branch and open template-based PR with explicit acceptance status.

## Dependencies and execution

T001 -> T002 -> T003 -> T006 -> T011. Documentation T004/T007 is sequential in the same
file. T005/T008 require authenticated Claude Code; T008 uses the completed session from
T005. T009 can proceed independently of live acceptance; T010 requires installed clients.
T012 follows implementation/verification; T013 follows review. No code agents are needed
until the required independent review.

Parallel examples: US1/US2 documentation research can run alongside backend tests;
US3 README links can run alongside isolated client syntax checks. All same-file edits
remain sequential. Deliver US1 first, add US2, then validate reproducibility. Actual live
acceptance stays unchecked when blocked even if documentation and automation are ready.

## Follow-up: real-agent integration testing

The 2026-11-07 live run passed T005. For T008, the operator verified that Codex
retrieved the imported refinement with its original provenance and sanitized
context. A fresh Codex search before import remains unverified. See
[verification.md](verification.md#t014-live-client-verification-2026-11-07)
for both results.

- [ ] T014 Verify shared memory with real Claude Code and Codex agents and record reproducible integration-test evidence in specs/028-coding-agent-access/verification.md.

T014 consolidates the live journeys in
[#71](https://github.com/nkz-soft/engineering-memory/issues/71). PR #70 delivered
the configuration, registration and backend regression.
