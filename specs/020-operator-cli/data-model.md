# Data model: Operator command line

No schema migration or new durable entity.

## CommandResult

Transient presentation object with schema version, command, semantic status, fixed error category and command-specific data. JSON keys, nullability, ordering and exit codes are defined in contracts/cli.md. Do not serialize arbitrary exceptions or settings models.

## RunReport / ConversationOutcome

Reuse ingestion/report.py. Counts and run status are derived properties and must be explicitly included in output. Completed timestamps and safe identity/stage information come from the pipeline. A terminal error is independent of failed-item count. CLI maps success to 0 and both partial_success/failure to 1.

## ImportRecord

Reuse ingestion/state.py: source/native id key, deterministic document id, raw content hash, recorded timestamp, imported/failed state and optional error. Latest write wins. Skips never transition durable state. Status displays an allowlisted subset, excluding content hash and arbitrary error text.

## Enumeration

Read-only protocol extension visits existing ImportRecords in source/source_id order; validate schema and model shape. Missing state maps to an empty status view; existing corrupt state raises the established typed error. No new status value or historical event table. Status is not evidence that every item from every earlier run was recorded: unidentifiable parser failures can exist only in transient run reports.

## Relationships and lifecycle

Command invocation owns configured adapters and closes them on all termination paths. Import consumes a source through IngestionPipeline. Provision invokes the existing provisioning service. Status depends solely on local state read access. No CLI-created identity, content timestamp, tag or secondary source of truth.
