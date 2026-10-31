# Tasks: Ingestion pipeline

Input: spec.md, plan.md, research.md, data-model.md and contracts/pipeline.md.

## Phase 1 — Setup

- [x] T001 Inspect existing boundaries, constitution and ignore rules; initialize locked environment using pyproject.toml.

## Phase 2 — Foundation

- [x] T002 Write failing aggregate/validation tests in tests/unit/test_ingestion_report.py, then implement immutable outcomes with UTC times, optional identity, failure-only diagnostics and derived counts in src/engineering_memory/ingestion/report.py.

## Phase 3 — US3: Safe traceable enrichment (P1)

Independent test: enriched sanitized conversation preserves identity/time and has correct provenance and tags.

- [x] T003 [US3] Write failing tests in tests/unit/test_enrichment.py, then implement pure enrichment in src/engineering_memory/normalization/enrichment.py.

## Phase 4 — US1: Failure-isolated import (P1, MVP)

Independent test: valid/broken/valid imports two and records one safe timed failure.

- [x] T004 [US1] Write failing ordering/isolation/source/interrupt contract tests in tests/contracts/test_pipeline.py.
- [x] T005 [US1] Implement sequential orchestration, safe operation logging and best-effort failed state in src/engineering_memory/ingestion/pipeline.py.

## Phase 5 — US2: Resume (P2) and US3 storage integration

Independent test: second import skips unchanged items; changed, failed and forced items reprocess under stable ids.

- [x] T006 [US2] Test raw-hash skipping, changed/failed/force and preserved successful records in tests/integration/test_ingestion_pipeline.py; implement skip handling in src/engineering_memory/ingestion/pipeline.py.
- [x] T007 [US3] Verify real source/sanitizer/classifier/archive/state composition and archive replay in tests/integration/test_ingestion_pipeline.py.

## Phase 6 — Verification and review

- [x] T008 Validate all suites, lint, formatting, diff and review; record outcomes in specs/018-ingestion-pipeline/quickstart.md.
- [x] T009 Update library contract and usage documentation in specs/018-ingestion-pipeline/contracts/pipeline.md, then create PR from .github/pull_request_template.md.

## Dependencies and strategy

T001 → T002 → T003 → T004 → T005 → T006/T007 → T008 → T009.
US1 uses US3 enrichment as a prerequisite; US2 adds rerun behavior. Each test is observed red before its implementation and green afterwards. Foundation report tests and enrichment tests could run in parallel because their files are independent; implementation is sequential here. US1 MVP proves isolated import, US3 proves privacy/persistence, US2 proves safe resumption. No extension hooks are configured.
