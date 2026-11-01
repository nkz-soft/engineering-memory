# Research: Import dry run

Research uses the checked-out implementation at origin/main 1b6472d, feature 020 contract,
state boundary and sanitizer report. A read-only research agent reviewed these integration points.
No external technology choice or new dependency is involved.

## R1: Share preparation and decision policy

**Decision**: Reuse `ingestion/state.py::may_skip` and extract pure preparation from
`ingestion/pipeline.py::_process`. Preview prepares predicted skips too.
**Rationale**: Current real skips occur before sanitization and have no project metadata.
**Alternatives considered**: Copying a separate pipeline causes policy drift; moving all ordinary
skips after preparation changes established behavior and adds unnecessary work.

## R2: Enforce read-only composition

**Decision**: Branch in `cli/runtime.py` before `state.initialize()` and `make_memory()`.
Use existing SQLite read-only mode plus validation, or an empty read-only view for missing state.
**Rationale**: A no-op retain alone would still write archives/state, including failure records.
**Alternatives considered**: Merely injecting a fake memory adapter cannot meet the requirement.

## R3: Metadata without content

**Decision**: Take unique sorted category names from sanitizer report counts; use enriched project
and original conversation timestamp. Use safe Stage diagnostics for failures.
**Rationale**: `sanitization/sanitizer.py` already returns categories; raw values are unnecessary.
**Alternatives considered**: Matched text, snippets and titles expose history without user value.

## R4: Sequential decision parity

**Decision**: Overlay projected successful records by source/native id in memory. Use original
pre-sanitization hashes. No predicted success after a preparation failure.
**Rationale**: A repeated unchanged id would otherwise be predicted to import twice.
**Alternatives considered**: A frozen starting-state lookup for every row differs from real ingestion.
Parity assumes successful real side effects and unchanged input, settings and initial state.

## R5: Separate preview output

**Decision**: Extend CLI with a distinct dry-run result shape and preserve ordinary schema-v1 output.
**Rationale**: Would-import is an intention and must not look like a durable imported outcome.
**Alternatives considered**: Reusing imported counters is ambiguous to operators and scripts.

All planning unknowns are resolved. No new architecture decision is required.
