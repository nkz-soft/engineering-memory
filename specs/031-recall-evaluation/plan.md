# Recall evaluation implementation plan

**Branch** `031-recall-evaluation`

**Date** 2026-11-07

**Spec** [Recall evaluation](spec.md)

## Summary

Ship an operator command that asks at least 30 fixed questions through MCP `search_memory`, scores topic coverage using deterministic matching, and compares complete reports. Validate the command with scripted responses, then publish two reports from live imports of the same synthetic corpus under different retain missions.

## Technical context

Use Python 3.13, uv, Typer, Pydantic v2, the existing MCP SDK, and pytest. Store the benchmark, synthetic ChatGPT export, project rules, and public results as versioned files. Keep archives, import state, credentials, and scratch output in operator-controlled local storage. Calls run sequentially, with a bounded deadline per tool call. Add no runtime dependency or network listener.

## Constitution check

| Principle | How the design complies |
|---|---|
| I. Raw archive | Seed through the existing importer. Each experiment keeps its own original and normalized archive, which supplies retrieval provenance. |
| II. Provenance and identity | Use fixed source IDs and timestamps in the corpus. Match expected topics only against the established document IDs in MCP results. Leave ID, tag, and deduplication semantics intact. |
| III. Test-first | Observe each new test fail before implementing its behavior. Cover validation and scoring, the MCP boundary, the CLI/report contract, and live import followed by recall. |
| IV. Replaceable boundaries | Use the public stdio MCP surface. Keep score calculation independent of transport. Engine administration stays with the existing provisioner during experiment setup. |
| V. Secrets | Use authored synthetic conversations, normal sanitization, and self-hosted memory. Publish only validated identifiers, topic outcomes, scores, and public experiment metadata. |

The pre-design and post-design checks have the same result. No constitution, engine contract, stack, bank strategy, or tag convention changes are proposed.

## Project structure

- `evaluation/recall-v1/` holds `benchmark.json`, `conversations.json`, `projects.toml`, and `results/`. Results include baseline, changed mission, and the comparison.
- `src/engineering_memory/evaluation/` contains validation and scoring, report validation and comparison, and the MCP client. `src/engineering_memory/cli/__init__.py` registers the evaluation command group.
- `tests/unit/test_recall_evaluation.py` covers schema, scoring, and reports. `tests/integration/test_recall_evaluation.py` covers the CLI and an actual stdio test server. The live experiment follows the quickstart.
- This feature directory holds the specification, research decisions, data model, CLI contract, and validation guide. Phase 2 generates the task list from these artifacts.

## Implementation sequence

Each slice starts by writing the test and observing it fail. Run the owning test file again after implementation and before committing the slice.

1. **Benchmark and scoring (FR-001, FR-002, FR-004).** Author at least 30 distinct questions, covering all seven categories, with topic aliases and supporting synthetic document IDs. Pin the corpus and project rules by digest. In `evaluation/benchmark.py`, implement `load_benchmark(path: Path) -> Benchmark` and `score_question(question: Question, matches: Sequence[RecallMatch]) -> QuestionOutcome`. Test exact and partial scores (one of two topics is 0.5), empty evidence, wrong provenance, multiword boundaries, duplicate evidence, and invalid dataset/corpus combinations.
2. **Read-only runner (FR-003, FR-005, FR-007).** In `evaluation/runner.py`, implement `async run_recall(benchmark: Benchmark, profile: RunProfile) -> RunReport`. Use one MCP session around the existing `serve` entry point. Validate tool results, enforce deadlines, score only the first ten results, and abort on protocol or tool failure. Test that all questions reach the server with the fixed tag and limit, and that a successful empty result differs from a malformed or failed response. Verify the child is closed on failure.
3. **Reports and operator commands (FR-005, FR-007).** In `evaluation/reports.py`, implement `write_report(report: RunReport, path: Path) -> None` and `compare_reports(baseline: RunReport, candidate: RunReport) -> Comparison`. Compare validated reports only when their benchmark, corpus, scoring version, project tag, limit, and question layout agree. Wire the Typer commands to these functions. Test the command exit codes, score deltas, incompatible and tampered input, no partial writes, and suppression of raw error and recall text.
4. **Controlled live evidence (FR-006, SC-003).** Use the [quickstart](quickstart.md) with a real extraction route and disposable instances. Verify import counts and record the measured baseline and changed scores with the public settings identifiers. Check report content and run repository lint, format, and pytest before requesting review.

## Review focus

- A valid but empty recall result contributes a miss. A tool error or invalid response aborts the run.
- Matching wording from a wrong source, repeated evidence, and a token embedded in another word cannot inflate the score.
- A changed corpus or edited question layout invalidates comparison even if the display label is the same.
- Report writes are atomic and preserve a prior completed file when a new run fails.
- A response with private-looking text or a tool exception with credentials cannot leak either into the report or command output.

## Complexity tracking

No deviations. The benchmark, scoring rules, and reports stay separate from the engine adapter and importer.
