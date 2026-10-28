# Tasks: Local Hindsight Deployment

## Setup and foundation

- [x] T001 Confirm approved plan/worktree, all 16 checklist items, absent hooks, existing ignore files and prerequisites in specs/014-local-hindsight-deployment/.
- [x] T002 Add failing httpx dependency expectation in tests/structure/test_packaging.py, then add httpx to pyproject.toml and uv.lock.

## US1 — Reproducible local instance

- [x] T003 [US1] Write failing deployment tests in tests/structure/test_hindsight_deployment.py for image pin, private ports, persisted volume, local providers, required proxy configuration and actual Compose validation.
- [x] T004 [US1] Implement deploy/hindsight/compose.yaml with loopback API, dedicated volume, explicit local providers, stable worker ID, required URL/alias and bounded health check.
- [x] T005 [US1] Document cross-platform setup/networking/resources/start/stop/restart in docs/development/local-hindsight.md.

## US2 — Configured proxy extraction

- [x] T006 [US2] Write failing settings/token/URL/privacy/error tests in tests/unit/test_hindsight_smoke.py, then implement safe transport/configuration in src/engineering_memory/memory/hindsight/smoke.py.
- [x] T007 [US2] Document external URL/key/alias and separate metadata-only proxy proof in docs/development/local-hindsight.md; no model setting or payload logs.

## US3 — Scratch-bank retain/recall

- [x] T008 [US3] Write failing tests in tests/unit/test_hindsight_smoke.py for generated unique banks, readiness/OpenAPI, synchronous retain, queued completion, expected-fact recall, deadlines and scoped cleanup.
- [x] T009 [US3] Implement synthetic-only Typer smoke module in src/engineering_memory/memory/hindsight/smoke.py with 180-second total deadline, positive options and keep-scratch; no arbitrary content/bank target.
- [x] T010 [US3] Document host test connectivity and pinned-route discrepancy for #16 in docs/development/local-hindsight.md and link it from README.md.

## Final verification and delivery

- [x] T011 Run focused/full pytest, Ruff lint/format, uv lock --check and git diff --check; record test-first evidence in specs/014-local-hindsight-deployment/verification.md.
- [ ] T012 **DEFERRED at operator request (2026-10-27):** Verify pinned image manifest, Compose config and live readiness/synthetic smoke/restart/proxy observation where the operator environment permits; record precise unverified prerequisites in specs/014-local-hindsight-deployment/verification.md rather than claiming mocked acceptance.
- [x] T013 Request independent read-only code review, fix findings, commit/push and open PR from .github/pull_request_template.md; attach PR and move #15 to in-review.

## Dependencies and tests

T001 → T002 → T003 → T004, followed by smoke tests before corresponding code. US1 is independently testable through Compose validation/readiness, US2 through transport tests plus separate proxy evidence, US3 through generated-bank write/read and cleanup. Deployment documentation and independent smoke tests can be authored separately, but edits to the shared module remain sequential. All three stories are approved scope. Live prerequisites may require the operator's existing proxy; mocks never count as live extraction evidence.
