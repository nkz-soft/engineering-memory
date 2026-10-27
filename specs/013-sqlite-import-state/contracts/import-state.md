# Contract: Persistent Import State and Refresh Decision

## Existing ImportState boundary

Preserve record(ImportRecord) -> None and find(Source, source_id) -> ImportRecord | None, with all existing IS-1 through IS-9 rules. find(None-equivalent) means unknown identity only. Never expose SQLAlchemy/sqlite3/OS/Pydantic exceptions through the boundary.

SQLiteImportState(path) is the concrete composition entry point; construction is inert. initialize() creates new storage or validates existing storage. validate() requires an existing compatible database and performs no schema creation. close() disposes resources. find/record require a successful initialize/validate. These lifecycle methods belong to the adapter, not the ImportState protocol. Composition (#19) passes Settings.import_state_path; adapter does not read configuration itself.

Read operations never contact archive, classifier, sanitizer or memory. Writes atomically replace one current outcome. No enumerate-for-reconciliation or removal method is introduced.

## Shared refresh decision

`may_skip(record, content_hash, *, force=False) -> bool`

| Remembered outcome | Hash | force | May skip |
|---|---|---|---|
| None | Any | Any | false |
| FAILED | Any | Any | false |
| IMPORTED | Equal | false | true |
| IMPORTED | Different | false | false |
| IMPORTED | Any | true | false |

Default calls remain backward compatible. Force is policy, never a fake hash or deleted state record. The existing test Pipeline gains run(now=..., force=False) and passes it through. Lookup still occurs; state failure does not become permission to retain. Production importer/CLI wiring is #19.

## Ordering and error semantics

For work that is not skipped: original normalized fingerprint → sanitize → classify/enrich → archive original and sanitized form → retain → record success. A boundary failure reports that conversation and records a safe failed outcome when storage permits, then processing continues. A skip does not rewrite state. Force follows the same processing path.

ImportStateUnavailable covers busy/locked/unreachable/IO/resource failures with bounded lock wait. ImportStateCorrupt covers invalid database, incompatible schema/version or malformed persisted records. Classify database errors by concrete codes/types, not generic OperationalError alone. Public messages are fixed, safe and exclude SQL, parameters, payload and raw backend messages; chained causes are diagnostic-only.

Failed record writes never claim success. If memory succeeded first, another run can resend with the same document identity; this boundary offers no exactly-once extraction guarantee across stores.

## Contract acceptance

Bind every shared suite hook, including unavailable/corrupt and reopen. Add subprocess persistence, transactional rollback, safe diagnostics and independent-reader tests. Integration acceptance counts memory calls over repeated/changed/failed/forced runs and checks actual missing-history survival in both local archive and fake bank. No live-engine assertion is substituted for these checks.
