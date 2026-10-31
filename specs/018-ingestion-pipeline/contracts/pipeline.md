# Pipeline library contract

Proposed public library surface; no network endpoint or CLI command is added.

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
