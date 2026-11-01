# Data model

No production schema changes.

- SyntheticConversation: one native ChatGPT id, historical creation time, decision text, project alias and repository clue. Produces stable chatgpt:<id> identity. Use synthetic data only.
- ExpectedEvidence: independently authored decision terms, source, source_id, project, known repository, importer version, original time and complete required tag set. imported_at must be valid run time, checked separately from original time.
- RunResources: unique network, disposable containers, scratch bank, temporary archive and SQLite path. Lifecycle: created -> ready -> provisioned -> imported -> verified -> removed; any failure transitions to cleanup and a failed run.
- ActualEvidence: RecallResult plus raw engine document_id, tags, mentioned_at and metadata. Correlate by stable document_id, never by result order or a relevance score threshold.
- GateReport: required case identities and outcomes; missing, skipped, failed or errored cases invalidate success.
