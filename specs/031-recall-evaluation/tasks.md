# Tasks — Recall evaluation

## Setup

- [x] T001 Confirm the branch and load the design from `specs/031-recall-evaluation/`.

## Foundation

- [x] T002 [P] Test and author the synthetic export, benchmark, and project rules in `evaluation/recall-v1/`.
- [x] T003 [P] Test strict loading and topic matching in `tests/unit/test_recall_evaluation.py` before implementing `src/engineering_memory/evaluation/benchmark.py`.

## User story 1 — Score a fixed set of questions

Independent check: Run the evaluator against a controlled stdio server and verify the aggregate, categories, and miss behavior.

- [x] T004 [US1] Test the run schema and scoring summaries in `tests/unit/test_recall_evaluation.py` before implementing `src/engineering_memory/evaluation/reports.py`.
- [x] T005 [US1] Test successful and failed stdio recall in `tests/integration/test_recall_evaluation.py` before implementing `src/engineering_memory/evaluation/runner.py`.
- [x] T006 [US1] Wire the tested recall CLI in `src/engineering_memory/cli/evaluation.py` and `src/engineering_memory/cli/__init__.py`.

## User story 2 — Measure a retain-mission change

Independent check: Compare compatible completed reports, then reproduce the comparison against separate live deployments.

- [x] T007 [US2] Test comparison, tamper detection, and atomic report writes in `tests/unit/test_recall_evaluation.py` and `tests/integration/test_recall_evaluation.py`. Implement the tested behavior in `src/engineering_memory/evaluation/reports.py` and `src/engineering_memory/cli/evaluation.py`.
- [ ] T008 [US2] Run the controlled comparison in `specs/031-recall-evaluation/quickstart.md` and commit live evidence in `evaluation/recall-v1/results/`.

## Verification

- [ ] T009 Run lint, formatting, and pytest. Review the whole branch against `specs/031-recall-evaluation/plan.md` before opening the PR.

T002 and T003 can be prepared independently. T004 through T006 build the scoring path. T007 consumes its reports. T008 requires the corpus and both operator commands. The first independently testable increment is US1.
