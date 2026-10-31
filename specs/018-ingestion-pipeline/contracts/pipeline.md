# Pipeline library contract

Implemented public library surface; no network endpoint or CLI command is added.

- `IngestionPipeline` accepts ConversationSource-independent collaborators: SecretSanitizer, ProjectClassifier, RawArchive, MemoryStore and ImportState, plus importer metadata and a UTC clock.
- `run(source: ConversationSource, *, force: bool = False) -> RunReport` consumes the source sequentially. One run uses one writer. The caller owns collaborator setup and lifetime.
- For each yielded SourceConversation: compute raw hash → state.find → may_skip. A skip produces only a report outcome. Otherwise sanitize → classify → enrich → archive.store → memory.retain → state.record(imported).
- Archive.store receives the original unchanged and sanitized enriched content. MemoryStore receives that same enriched content after archive completion.
- Recoverable SourceFormatError is reported and the same iterator is pulled again. Other terminal iterator failures are a run-level error; no silent restart or unbounded retry.
- Item exceptions produce one failed outcome and do not escape to prevent the next item. Failed state recording is attempted only with complete identity/hash; its failure is retained as a secondary safe diagnostic.
- Interrupts and termination propagate. Adapter retries remain owned by adapters; pipeline retries do not multiply them.
- Reports contain imported/skipped/failed outcomes, UTC failure times and available identity. No raw exception text or conversation payload is exposed.
- Semantic aggregate status is success, partial_success or failure, following data-model.md. CLI exit-code mapping is outside this contract.

Acceptance: ordered-spy contract tests plus integration with real local archive and SQLite state, using synthetic conversations and a fake MemoryStore. No concrete engine types may enter pipeline signatures or implementation.

## Import paths and composition

```python
from engineering_memory.ingestion.pipeline import IngestionPipeline
from engineering_memory.ingestion.report import RunStatus

pipeline = IngestionPipeline(
    sanitizer=sanitizer,
    classifier=classifier,
    archive=archive,
    memory=memory,
    state=state,
    importer_version="0.1.0",
)
report = pipeline.run(source, force=False)
if report.status is RunStatus.PARTIAL_SUCCESS:
    # A CLI caller can map this semantic status to its documented exit code.
    pass
```

Adapters and sources are provided by the caller. Initialize or validate the import-state adapter before a run; provision the memory bank separately. Pipeline construction performs no I/O. Optional constructor keywords are `bank` (logging context, default `engineering-global`), `repository`, `user` and `clock` (aware UTC datetime callable). No adapter is implicitly closed.

`RunReport.outcomes` contains immutable `ConversationOutcome` values. Counts `imported`, `skipped`, `failed` and aggregate `status` are derived properties. `terminal_error` describes a failed source read without inventing a conversation. Item `error` is a fixed `Stage` value; `state_record_failed` indicates that persisting failure state also failed. Parser subjects that cannot be valid native identifiers become `None`. Reports retain metadata, never conversation payloads.

Diagnostic emission is best effort so logging sink failures do not discard the report. Import-state failures remain represented in outcomes. Numeric process exit codes and CLI options belong to #21.
