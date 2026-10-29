# Tasks: Full-product Compose

Input: spec.md, plan.md, research.md, data-model.md and contracts/lifecycle.md.
Approved planning gate: user reran /issue-to-pr 55 on 2026-10-29.

## Phase 1 — Setup

- [x] T001 Recheck main prerequisites and record missing product contracts in specs/015-full-product-compose/research.md.
- [x] T002 Resolve immutable LiteLLM image pin and shared Compose strategy in deploy/product/compose.yaml.

## Phase 2 — Foundation

- [x] T003 Write and observe failing infrastructure tests in tests/structure/test_product_deployment.py.
- [x] T004 Add canonical engine service and retain engine-only compatibility in deploy/hindsight/compose.yaml and deploy/hindsight/service.yaml.

## Phase 3 — US1: Repeatable development (P1)

Independent test: effective configuration, missing-input errors, dependency readiness; full provisioning pending upstream.

- [x] T005 [US1] Implement internal/external proxy variants and persistent application storage in deploy/product/compose.yaml and compose.external.yaml.
- [x] T006 [US1] Add failing preflight/deadline tests in tests/unit/test_product_runner.py.
- [x] T007 [US1] Implement bounded dependency/start/stop commands in deploy/product/run.py.
- [ ] T008 [US1] Bind actual idempotent provisioning/import/status/MCP commands in deploy/product/compose.yaml once #17/#21/access prerequisites land; fail closed meanwhile.

## Phase 4 — US2: Isolated live E2E (P1)

Independent test: lifecycle fault tests and concurrent identities offline; actual import/retrieval requires upstream.

- [x] T009 [US2] Write failing identity, owned cleanup, cancellation and timeout tests in tests/unit/test_product_runner.py.
- [x] T010 [US2] Implement isolated Compose override and runner cleanup in deploy/product/compose.e2e.yaml and run.py.
- [ ] T011 [US2] Integrate real product scenario from #23/#24 in deploy/product/compose.yaml; keep a visible skip until available.
- [ ] T012 [US2] Verify provider-backed import, MCP retrieval, archive/provenance, unchanged re-import, persistence and two concurrent live runs; record evidence in specs/015-full-product-compose/validation.md.

## Phase 5 — US3: Offline and operator experience (P2)

Independent test: full offline suite and explicit live skipped status without secrets.

- [x] T013 [US3] Add live prerequisite/skip and secret-safe diagnostics tests in tests/unit/test_product_runner.py.
- [x] T014 [US3] Document configuration, reset, CI, Windows/Linux and pending prerequisites in docs/development/full-product.md and deploy/product/.env.example.

## Phase 6 — Verification and review

- [x] T015 Run full pytest, ruff and effective Compose checks; record exact evidence in specs/015-full-product-compose/validation.md.
- [ ] T016 Request independent code review, fix findings, and open draft PR using .github/pull_request_template.md with upstream blockers explicit.

## Dependencies and execution

T001 -> T002/T003 -> T004 -> T005 -> T006/T007 -> T009/T010 -> T013/T014 -> T015/T016.
T008 and T011 depend on upstream product features; T012 depends on both and provider configuration.
Tests must fail before implementation. Infrastructure first is the approved incremental scope (FR-013); pending tasks remain unchecked and the PR remains draft.

Parallel opportunities: documentation in T014 can proceed independently of lifecycle implementation; Compose structure and runner tests touch different files. Execution here is sequential; independent review occurs after implementation.

Blocked task detail: T008/T011 require real product capabilities absent on main; their service roles currently fail closed. T012 requires those tasks plus a configured provider and platform runs. No live acceptance is marked done.
