# Data Model: Persistent Import State

## Version 1 tables

### import_state_schema

| Column | Type | Constraint |
|---|---|---|
| singleton | Integer | Primary key; exactly one row with value 1 |
| version | Integer | Required; value 1 |

Initialize both tables and the version row in one explicit transaction. A truly empty database may be initialized. Existing tables without a valid version marker, missing columns, unsupported version or incompatible constraints are corruption, not a prompt for automatic reset. Do not claim create_all alone verifies schema compatibility: validate expected tables/columns, primary key and constraints explicitly.

### import_records

| Column | Type | Domain meaning |
|---|---|---|
| source | Text | Existing Source value; composite primary key member |
| source_id | Text | Opaque nonempty native identifier; composite primary key member |
| content_hash | Text | Nonempty existing canonical fingerprint before sanitization |
| document_id | Text | Existing stable nonempty document identity |
| recorded_at | Text | UTC ISO-8601 instant, fixed six fractional digits, explicit +00:00 |
| status | Text | imported or failed only |
| error | Nullable Text | Required nonempty for failed; NULL for imported |

All columns except error are NOT NULL. Primary key is `(source, source_id)`; there is no identity-only unique key. Add CHECK constraints for allowed persisted statuses and failure/error pairing. Validate reconstructed rows through ImportRecord, including source and timestamp types. The adapter stores fields provided by callers rather than inventing identifiers or enforcing a stricter hash format than the existing model.

## State transitions

- Unknown + import success → IMPORTED with current fingerprint and attempt clock.
- Unknown or prior outcome + failure → FAILED with current attempted fingerprint and safe error.
- IMPORTED + equal fingerprint + ordinary refresh → report skipped; no stored mutation.
- IMPORTED + changed fingerprint, FAILED, unknown, or explicit force → process; persist resulting success/failure.
- Missing from export → no lookup/diff/removal operation; stored outcome remains untouched.

There is one current row per conversation, no attempt log. Last completed write wins even if a caller supplies an older recorded_at; timestamp is data, not concurrency control.

## Atomicity and lifecycle

A single writer updates all row fields in a transaction committed before return. Rollback preserves the old row. Readers see a complete committed outcome or an explicit unavailable error. No global transaction joins archive, memory and state. Construction performs no I/O; initialize creates/validates, validate opens existing storage for readers, close disposes resources. Methods refuse absent or invalid schema without treating it as an empty corpus.

## Privacy and portability

No original or sanitized bodies, tokens or raw exceptions are stored. The caller is responsible for a safe error string under E5. Bind identifiers/values as parameters. SQLAlchemy remains in the adapter; PostgreSQL can implement the same protocol later without ingestion changes. This is a local schema-version policy, not a claim that SQLite files themselves migrate to PostgreSQL automatically.
