# Implementation Plan: Evidence-grounded Deep Recall

**Branch**: `034-deep-recall` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

## Summary

Add a shared read-only operation behind `engineering-memory deep-recall` and MCP `deep_recall`. Run a small search plan under the caller's project, merge candidates by document ID, and synthesize a timeline from bounded sanitized archive evidence. Bind every returned entry to that request's evidence and render quotes from the archive.

## Technical context

Use Python 3.13, Pydantic v2, the existing Typer and stdio MCP surfaces, and httpx for the optional, explicitly configured OpenAI-compatible synthesis adapter. Keep existing shared-bank recall and normalized archive contracts. No new storage, SDK, or background work. See [research.md](research.md) for the design tradeoffs and [contracts](contracts/deep-recall.md) for limits and compatibility behavior.

## Constitution check

| Principle | Design and verification |
| --- | --- |
| I. Raw archive is the source of truth | Recall results nominate sessions; the sanitized normalized archive supplies every citation, time, and quote. Replay and originals are untouched. |
| II. Provenance and stable identity | Reuse source-derived document IDs and original message times. Compare indexed provenance, archive provenance, document ID and exact project tag. Anchors are offsets in the current normalized record. No changes to import or deduplication. |
| III. Test-first | Observe each new boundary or scenario test fail before writing the implementation. Include import-to-recall across Claude Code and Codex, scope abuse, budgets, citation validation, and CLI/MCP contracts. |
| IV. Replaceable boundaries | Put orchestration in access and call the existing memory and archive interfaces. Add a narrow synthesis protocol and compose its adapter at the CLI runtime boundary. No Hindsight reference in access. CLI and MCP call the same service. |
| V. Secrets | Read sanitized normalized records only. Send only verified project excerpts to the explicitly configured endpoint. No auto-discovery, redirects, raw archive reads, private error details, content logging, or new MCP transport. |

No deviation or governance amendment is needed. This is Phase 3 synthesis over the existing access surface, without changing supported history sources or bank policy.

## Implementation sequence

1. **Scoped retrieval and archive evidence.** In `access/deep_recall.py`, implement a testable read coordinator using the same ID and project validation as `access/service.py`. Define strict request/result types and an evidence manifest. Search in plan order, deduplicate within and across queries, rank by best per-query rank then document ID (scores need not be comparable). Process one bounded archive load per selected document. Check identity and provenance before slicing messages; reject scope conflicts and never pass recall snippets to synthesis. Add red/green tests with a recording memory adapter and archive.
2. **Synthesis and anchors.** Define a narrow `DeepRecallSynthesizer` protocol in access with one request containing the question and validated evidence, and one structured response of entry text and evidence selectors. Put the HTTP adapter behind that protocol and compose it in `cli/runtime.py`. Extract the quote normalization and matching logic used by `_verify_evidence_quotes` into a shared helper and retain existing project model tests. Validate selectors against the exact prompt manifest, extract quotes from archive text, and sort by canonical evidence time. Use a short total timeout, response byte cap, and no automatic retries. Fake the protocol in unit tests and exercise the HTTP contract with a mock transport; cover adversarial selectors, quote payloads, and output size.
3. **CLI and MCP.** Route both through `MemoryAccess.deep_recall` in `access/service.py`. Register the MCP tool in `access/server.py` and the command in `cli/__init__.py` (or a focused CLI module). Add optional access settings for the endpoint and model; use the existing environment and secret conventions. Existing commands/tools must work with synthesis absent. Add CLI runner and real stdio MCP contract tests, and document setup, data sent and result interpretation.
4. **Acceptance.** Use synthetic native source fixtures and the existing import contracts. Load them through the real archive and use deterministic scoped recall and synthesis fakes for the required cross-source result; include a foreign lookalike. Add an opt-in configured backend smoke check that uses an isolated bank and synthetic data. Run [quickstart.md](quickstart.md), regress prior access/model behavior and share commands and outcomes in the PR.

## Risks and boundaries

The archive interface loads a normalized record before paging. The proposed caps bound calls, selected pages, and data sent to synthesis; they do not bound bytes decoded by one archive load. Physical streaming of large records is separate work. Timestamp and citation verification establish provenance and verbatim accuracy, not semantic entailment; surface conflicting or incomplete evidence and make every entry inspectable. No unresolved clarification is required for the proposed first release.
