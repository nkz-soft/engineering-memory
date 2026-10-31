# Implementation Plan: Ingestion pipeline

**Branch**: `018-ingestion-pipeline` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)
**Input**: Issue #19 and `specs/018-ingestion-pipeline/spec.md`

## Summary

Compose existing synchronous boundaries into a sequential pipeline with per-conversation isolation, state-based skipping, safe enrichment, archive-before-retain ordering and a typed aggregate report. Source adapters already parse and normalize; no duplicate normalization stage is introduced. Implementation begins only after human review of this plan.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: Existing Pydantic v2 models, boundary protocols and structlog/OpenTelemetry helpers; no new dependency.
**Storage**: Injected RawArchive and ImportState; production composition uses existing local archive and SQLite adapters.
**Testing**: pytest unit, contract and integration suites; synthetic data only.
**Target Platform**: Existing Windows/Linux Python environments and Docker.
**Project Type**: Internal library orchestration for the later Typer CLI.
**Performance Goals**: Start downstream processing before requesting the next conversation; no new full-export materialization.
**Constraints**: Sequential single writer, no contents or credentials in diagnostics, no concrete engine imports, archive durable before retain.
**Scale/Scope**: Thousands of conversations; report metadata grows with outcome count, conversation payloads are not accumulated by orchestration.

## Constitution Check

| Principle | Before research | After design |
|---|---|---|
| I — Raw archive | Pass: both forms saved before retain | Pass: archive failure prevents retain; replay adapter remains usable |
| II — Identity/provenance | Pass: existing identity/hash models reused | Pass: raw hash for skip; original timestamps; enrichment supplies metadata and tags |
| III — Test first | Pass: failing test precedes each implementation slice | Pass: ordered-call, isolation, privacy, retry/resume and report tests planned below |
| IV — Boundaries | Pass: depend on protocols only | Pass: source parsing remains in adapters; each stage independently testable |
| V — Secrets | Pass: sanitization before classify/enrich/archive-normalized/retain | Pass: original bytes stay local; safe failure codes and no exception text in reports |

No principle, stack entry, history source, bank strategy or engine contract changes. No ADR required. Rechecked after the design below; no deviations.

## Project Structure

```text
specs/018-ingestion-pipeline/
  spec.md
  plan.md
  research.md
  data-model.md
  contracts/pipeline.md
  quickstart.md
  checklists/requirements.md
src/engineering_memory/ingestion/
  pipeline.py               # orchestration and injected dependencies
  report.py                 # immutable per-item and aggregate results
src/engineering_memory/normalization/
  enrichment.py             # pure enrichment of sanitized conversation
 tests/unit/test_ingestion_report.py
 tests/unit/test_enrichment.py
 tests/contracts/test_pipeline.py
 tests/integration/test_ingestion_pipeline.py
```

**Structure Decision**: Keep orchestration with ingestion and provenance construction with normalization. Existing adapters remain unchanged unless a test demonstrates a contract defect. No CLI or settings wiring in this feature.

## Design and Implementation Sequence

1. Define immutable outcomes and aggregate status, test count reconciliation and every aggregate case first. Preserve `ImportStatus` vocabulary; introduce a separate run status.
2. Test then implement pure enrichment from sanitized Conversation plus ProjectTag, importer version, clock time and optional user/repository metadata. Produce source/project/type tags once and preserve original timestamps and identity.
3. Test then implement `IngestionPipeline.run(source, force=False)`. Inject sanitizer, classifier, archive, memory store, state, importer metadata and a UTC clock. Pull explicitly with `next()` so a recoverable `SourceFormatError` does not close the consumer loop. Do not catch BaseException.
4. For a yielded pair, capture native identity and raw normalized hash, call state.find and shared may_skip, then sanitize → classify → enrich → archive.store → memory.retain → state.record(imported). No downstream calls or state write for a skip.
5. Catch item exceptions at the item boundary and emit a safe stage/error category, never `str(exception)`. Attempt a failed ImportRecord only when source id, raw hash and document id are known. If record itself fails, preserve the primary failure plus a safe state-write diagnostic. Never mark the item imported after state persistence fails.
6. Handle recoverable source errors as failed outcomes using `subject` when provided, without inventing a native id/hash. A terminal read/unavailable error ends the loop and becomes a run error. Previously produced results remain available.
7. Integrate existing operation logging without allowing its raw exception rendering to leak private details: contain arbitrary exceptions before they reach the operation context, and emit only safe pipeline errors. Test logs with synthetic secret sentinels. Retain adapter retry ownership and stable ids.
8. Add integration coverage using real ChatGPT source, sanitizer, deterministic classifier, local archive and SQLite state with a recording fake MemoryStore. Validate archive replay and unchanged/changed/force/failed reruns. Run existing boundary suites to guard replaceability.

## Validation Strategy

Observe red then green for each slice. Ordered spies prove state check precedes processing, classification sees sanitized data, archive precedes retain and successful state follows retain. Inject failures at source, state read, sanitizer, classifier, enrichment, archive, retain and state write; verify following items run. Cover missing parser identity, empty and all-skipped runs, terminal source failures after progress, unknown project, original timestamps, safe diagnostics and interrupts. Compare stored original bytes exactly and assert normalized/retained/report/log data never contain synthetic secrets.

Commands and expected results are in [quickstart.md](quickstart.md). This phase creates documentation only; no implementation tests are claimed as passing.

## Alternatives Considered

- Batch parse/transform/write: rejected as in issue #19; malformed items block progress and payload materialization grows with the export.
- Concrete adapter construction inside pipeline: rejected; violates replaceability and makes failure-order tests depend on infrastructure.
- Retry at pipeline and adapter layers: rejected; multiplies requests and retry budgets. Adapter retry semantics already own transient classification and idempotency.
- Numeric process exit inside library: rejected; expose semantic run status and let #21 map it to command exit codes.

## Complexity Tracking

No constitution violations or additional infrastructure. Report metadata is intentionally retained for callers; large-run streaming reports can be a separate measured need.

## Implementation notes

Implementation uses the existing shared logger and `ingestion.operation` event schema directly rather than wrapping processing in `ingestion_operation`: that context manager formats arbitrary exception messages, while this pipeline must emit only fixed safe stage categories and attach the project resolved during processing. Logging sink failures are best effort and cannot abort ingestion. The optional clock is expected to provide aware UTC timestamps. Invalid parser subjects are treated as unknown identities rather than allowed to break report validation.

Tasks and integration coverage live in tasks.md and tests/integration/test_ingestion_pipeline.py. Unit coverage of orchestration is consolidated in tests/contracts/test_pipeline.py; a duplicate unit harness is unnecessary. No new dependencies or boundary changes were needed.
