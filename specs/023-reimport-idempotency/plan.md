# Implementation Plan: Prove re-import idempotency

**Branch**: `023-reimport-idempotency` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)
**Input**: Issue #24 and specs/023-reimport-idempotency/spec.md

## Summary

Extend the existing required live end-to-end gate to prove both independent idempotency layers and selective updates. Reuse the real pipeline, local archive, SQLite state, pinned Hindsight instance and deterministic extraction fixture introduced for #23. Observe retain identities through a forwarding spy and extraction-call deltas through fixture statistics; derive document identity counts from complete recall evidence for a small, controlled corpus.

## Technical Context

**Language/Version**: Python 3.13, uv.
**Primary Dependencies**: Existing pytest, httpx, testcontainers-python and production adapters; no added dependencies.
**Storage**: Per-case temporary local archive and SQLite; disposable live-engine banks.
**Testing**: Offline assertion controls and runner completeness tests; three required live cases.
**Target Platform**: Docker-capable developers and Linux CI.
**Project Type**: Modular monolith with CLI and external memory engine.
**Performance Goals**: Preserve existing runner deadlines (600-second startup, 420-second pytest, 90-second cleanup); keep corpus to two short conversations per scenario.
**Constraints**: No credentials, real conversations, protocol changes or bank/tag strategy changes; no mocked engine on the live path.
**Scale/Scope**: Phase 1 item 8 and section 17 only. Dependency #23 is closed and merged in base fd65de6.

## Constitution Check

Pre-research and post-design checks PASS:

| Principle | Compliance |
|---|---|
| I — Raw archive | Run real archival persistence and verify original and sanitized normalized forms; delete only test-owned state for recovery. |
| II — Provenance and identity | Independently define source-derived expected identities; unchanged replay proves skip and no extraction; recovery proves upsert; edit preserves identity. |
| III — Test-first | Phase 2 first writes failing assertion/runner controls and missing live scenarios, observes failure, then adds helpers and only necessary fixes before green. |
| IV — Replaceable boundaries | Pipeline-facing observer forwards MemoryStore calls unchanged; engine-specific recall and extraction statistics stay in integration infrastructure. No domain or interface expansion. |
| V — Secrets | Use synthesized conversations, local fixture extraction, temporary storage and test-owned bank cleanup. Do not log corpus bodies or secrets. |

Fixed stack and production shared-bank convention remain unchanged. Scratch banks are existing test isolation. No deviation or ADR is required.

## Project Structure

```text
specs/023-reimport-idempotency/
  spec.md
  plan.md
  research.md
  data-model.md
  contracts/reimport.md
  quickstart.md
  checklists/requirements.md
tests/integration/test_import_recall_e2e.py
tests/integration/hindsight_contract/llm.py  # existing /stats, reuse unchanged if possible
deploy/hindsight/e2e.py
tests/unit/test_e2e_runner.py
```

**Structure Decision**: Extend the existing module and its selected-case manifest rather than introduce a second Docker lifecycle. Prefer test-local helpers; no production code changes unless a failing regression identifies a defect within scope.

## Design and execution

1. Define two short synthetic conversations with distinct stable ids and expected fact markers accepted by the extraction fixture. Keep literal expectations independent from enrichment/serialization output.
2. Reuse the per-case scratch bank fixture and real pipeline adapters. Record baseline successful import, archive forms, identities recalled and fixture statistics after synchronous retain completion.
3. Wrap the real MemoryStore in a test-local forwarding recorder to capture submitted document identities without changing payload, return values or exceptions. Verify recorder controls; submission counts supplement recall and never substitute for it.
4. Unchanged case: replay the identical export against intact state. Assert both skips, zero failures, no forwarded retains, zero extraction-call delta and the exact recalled identity set with expected facts.
5. Recovery case: establish an independent baseline, close/dispose state connections and remove only that test's SQLite files. Recreate an empty state store and a fresh memory adapter against the same archive/bank to exclude in-process retry state; assert two real submissions with original identities and unchanged recalled document set. Do not assert zero extraction in recovery.
6. Edit case: independent baseline with intact state; change one conversation's fact while retaining its source id. Assert exactly that identity is submitted, one import/one skip, updated fact recall under the same identity and preserved unchanged fact. Verify the superseded controlled fact is absent once the replacement is visible.
7. Recall evidence: aggregate all returned rows for a bounded broad corpus query plus specific queries for every corpus member and changed version. Compare distinct document_id values to independently specified expectations, require every expected fact, reject unknown ids. With deterministic one-fact-per-document extraction also check per-document fact cardinality, so duplicate fact rows under one id cannot be hidden by a set. Set sufficiently large supported recall budgets/token limits for this two-document bank; do not claim recall enumerates arbitrary production banks. Use bounded polling for visibility only; missing/truncated evidence is failure.
8. Capture fixture /stats deltas at stable completed boundaries. Keep scenarios serial because counters are server-wide; any extraction errors fail the scenario. Zero retain submissions plus zero extraction delta establish no repeated extraction cost without a billing service.
9. Add three explicit required JUnit identities to deploy/hindsight/e2e.py; existing required scenarios remain. Update test_e2e_runner completeness controls so each missing/skipped/error/failure case is rejected.
10. Add independently constructed negative evidence for omitted document, unexpected document, duplicate controlled fact, redundant retain/extraction and wrong changed identity. Verify each validator rejects the corruption. If a production defect is found, isolate its failing regression before fixing it.
11. Run offline tests, lint/format and existing live contract plus extended E2E runners. Record actual commands and red/green output in Phase 2. Repeat clean E2E to verify teardown and independence.

## Alternatives considered

- Importer-only tests: rejected by issue; state loss removes the protection being measured.
- Import-state totals as document counts: circular and cannot prove backend upsert.
- Mocked memory store: cannot prove live document replacement.
- Raw recall row count alone: one document may produce multiple facts; deterministic fixture permits an additional explicit cardinality check but distinct identities remain the document metric.
- Zero extraction after state loss: outside section 17's guarantee; stable identity is not equivalent to an extraction cache.
- A new runner or paid extraction provider: existing isolated credential-free harness already supplies the required evidence.

## Complexity Tracking

No constitutional violations. No unresolved clarification. Implementation must verify supported recall limits against the pinned running engine, rather than infer completeness from a first-hit helper.

