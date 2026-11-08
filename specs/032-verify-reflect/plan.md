# Implementation Plan: Verify Reflect on the Accumulated Corpus

**Branch**: `032-verify-reflect` | **Date**: 2026-11-08 | **Spec**: [spec.md](spec.md)

**Input**: [Issue #31](https://github.com/nkz-soft/engineering-memory/issues/31) and ARCHITECTURE.md §§16, 21–22.

## Summary

Expose the read-only `reflect` operation from §16.1 on the existing MCP surface and use it alongside `search_memory` for a paired evaluation. Reuse the existing evaluation client's MCP setup and report-writing utilities where their contracts fit. Keep live inputs and reviewer notes under ignored local storage. Publish aggregate results and the operator's consumer routing rule.

## Technical Context

| Area | Design |
| --- | --- |
| Runtime and dependencies | Python 3.13, uv, existing httpx, Pydantic v2, MCP SDK and Typer |
| Storage | Existing self-hosted Hindsight bank, sanitized archive, and ignored local evaluation files |
| Testing | pytest unit and boundary tests, stdio integration tests, opt-in pinned-engine contract and accumulated-corpus runs |
| Platform | Existing Windows and Linux local workflows and stdio transport |
| Performance | Measure end-to-end duration per call. Report median and range with counts. Capture token usage only if the pinned engine exposes it safely. |
| Constraints | One stable corpus, strict project scope, read-only consumer access, reviewed aggregates for publication |
| Scope | Six or more synthesis questions across two classes and two or more direct lookup controls. |

## Constitution Check

| Principle | Plan and post-design check |
| --- | --- |
| I. Raw archive is the source of truth | The evaluation reads the bank and checks evidence through the existing sanitized archive path. The run creates evaluation records only. |
| II. Provenance and stable identity | MCP references require matching archived provenance and project. Keep canonical conversation IDs in local evidence and expose them through the existing consumer citation contract. |
| III. Test-first | For each behavior change, observe focused tests fail before implementation. Verify mapping with contract tests, the normal stdio path with synthetic data, and behavior against the running pinned engine. |
| IV. Replaceable boundaries | The Hindsight adapter owns the wire contract. A separate read-only synthesis protocol beside the existing memory interface leaves ingestion callers and structural checks on `MemoryStore` intact. The evaluator calls only MCP. |
| V. Secrets stay out of the engine | Send operator-authored questions through the existing self-hosted path. Only sanitized archive evidence is served. Keep prompts, answers, references, provider errors and credentials out of published artifacts and logs. |

All five gates pass at design review. The plan introduces no dependency, ingestion, bank, or tag policy changes. Phase 3 explicitly includes reflect verification, and §16.1 schedules the tool when a feature needs it.

## Project Structure

- `memory/interface/store.py` and `memory/interface/__init__.py` define and export engine-neutral synthesis types.
- `memory/hindsight/store.py` and its existing serialization and HTTP helpers implement the pinned engine mapping and failure translation.
- `access/` registers and serves the read-only MCP tool using existing sanitized archive provenance checks.
- `evaluation/runner.py` and `cli/evaluation.py` supply the existing stdio evaluation setup and CLI entry point. Add the paired runner and report models under `evaluation/` without modifying the recall benchmark schema.
- `tests/unit/`, `tests/contract/` and `tests/integration/` cover behavior at the existing seams.
- `docs/operations/` contains the public comparison and consumer instructions. See [quickstart.md](quickstart.md) for the operator run.

## Implementation Sequence

1. Add the synthesis reader and pinned adapter mapping. Test strict project scoping, evidence fields, empty evidence, malformed responses and failure mapping before implementation. Verify actual response fields and configured model behavior against the running pinned engine. See [research.md](research.md).
2. Register MCP `reflect` as a read-only tool. Test successful references, duplicate and wrong-project evidence, missing archive evidence, and refusal on an empty validated set or known cross-project evidence. Verify with the stdio client and synthetic retained data.
3. Add the paired evaluation runner using `evaluate reflect`. Test identical prompts and scopes, independent timing, continued recording after a case-level failure, terminal transport failure with an incomplete run, and private report output (including path escape rejection) before implementation. Keep the human rubric in the run guide.
4. Freeze cases and expected evidence, run both operations on a stable accumulated bank, review the pairs, and publish the aggregate comparison and consumer guidance. Verify that a second operator could follow the guide, including how to report inconclusive results.

## Alternatives Considered

- **Use reflect for every query.** §16 assigns lookup to recall. The lookup controls test whether synthesis adds enough to justify its measured overhead in that use case.
- **Use direct engine calls.** Running through MCP measures the consumer path and exercises provenance checks.
- **Use the #32 synthetic dataset alone.** It supports repeatable offline and fixture checks. The accumulated bank is required to answer #31's real-history question.
- **Score answers with literal topic matching alone.** Keep the existing recall benchmark for its intended purpose. Manual review of frozen expectations can distinguish paraphrases, reversed chronology, and unsupported cross-source conclusions.
