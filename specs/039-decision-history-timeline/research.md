# Research — Source-Backed Decision History

## Retrieve evidence on demand through Deep Recall

**Decision** Share the project-tagged candidate search, bounded normalized archive reads, opaque passage selectors and citation verification from `access/deep_recall.py`. Use a decision-specific structured synthesis draft and the existing configured synthesis transport.

**Rationale** Deep Recall already checks both recall-hit and archive provenance, bounds the work and resolves message-level evidence. Its existing response stores free-form entries with a single uncertainty flag. A decision view needs explicit event types, action evidence and competing accounts. Citation validation checks anchor identity and quotes. The model's interpretation remains a synthesis users can check against the sources.

**Alternatives considered** The issue supplied no alternatives. The standing decisions model is useful for discovery but its snapshot cannot reconstruct prior versions or their exact dates. Parsing existing answer prose would make lifecycle and conflict semantics depend on wording. A persisted event index would introduce ingestion, storage and reconciliation work for a read-only feature.

## Extend the existing browser Deep Recall operation

**Decision** Accept an optional decision-history mode at the existing Deep Recall route and dispatch to a separate method on the shared read service. Keep the ordinary Deep Recall browser and MCP shapes compatible.

**Rationale** Both views answer project-scoped questions from the same evidence and use the same authorization and synthesis configuration. This preserves ADR-014's three read operations and existing message viewer. The mode is selected by the operator, never by archived text.

**Alternatives considered** A separate route would expand ADR-014's allowlist for work already served by the synthesis operation. A new decision catalog would require durable identities and discovery commitments absent from #85.

## Derive chronology from the action source

**Decision** Use the timestamp of the archived message that supports the action. Preserve a distinct unknown or disputed state. Sort verified timestamps as instants and flag ties. Require separately anchored competing accounts for an unresolved conflict.

**Rationale** An older corroborating passage cannot date an action in a later session. A model-provided date, import time or conversation start cannot establish the action message time. A stable tie-break supports reproducible display while the view communicates that ordering is uncertain.

**Reference** [Hansard Deep Recall](https://www.hansard.dev/guides/deep-recall/) describes inspecting evidence across sessions and opening sources from citations. It informs the evidence interaction.
