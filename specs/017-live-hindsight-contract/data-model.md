# Data Model: Live Hindsight Contract

No production schema changes.

| Entity | Fields | Rules |
|---|---|---|
| Scenario | name, architecture sections, expected document set | positive and negative assertions; independent scratch resource |
| ScratchBank | unique generated id, created flag, cleanup status | cannot equal engineering-global; delete only generated ids |
| SyntheticDocument | source id, document_id, text, tags, original timestamp | stable chatgpt:<id>; synthetic content only; aware dates |
| OperationObservation | operation_id, status, completed_at, extraction count | pending/processing -> completed; failure/timeout fails; replay preserves completed operation |
| TagExpectation | literal wire mode, requested tags, expected ids | overlapping/disjoint/exact/untagged cases; explicit inclusion and exclusion |

Replacement changes a document's content while retaining its identity. Retry retains both payload and operation identity. Historical records use distinct original dates independent of insertion order. Extraction counters are test observations, never production metrics or billing claims.
