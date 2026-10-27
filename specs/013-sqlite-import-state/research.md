# Research: Persistent Import State

## R1 — Reuse the existing boundary and policy

**Decision**: Implement ImportState.record/find without changing their signatures. Extend centralized may_skip with a keyword-only force=False argument, preserving existing calls.

**Rationale**: ingestion/state.py already defines status validation, original normalized content hash and last-write semantics. tests/contracts/state.py supplies IS-1 through IS-9, including reopen. There is no reason for adapters to own skip decisions.

**Alternatives considered**: adapter-specific skip, persisted SKIPPED, a second hash function; all contradict established contracts.

## R2 — SQLAlchemy Core and local transactions

**Decision**: Use SQLAlchemy 2 Core, bound statements, short engine.begin scopes, portable keyed select/update-or-insert, and a single writer.

**Rationale**: [SQLAlchemy transaction documentation](https://docs.sqlalchemy.org/en/20/core/connections.html#connect-and-begin-once-from-the-engine) specifies commit/rollback scope. Our single-writer assumption makes a portable update-or-insert sufficient; no ORM identity map is needed.

**Alternatives considered**: native sqlite3 bypasses ADR-004; dialect-specific UPSERT is unnecessary; concurrent importers require another design.

## R3 — Driver details and time

**Decision**: Set Python 3.13 sqlite transaction control to autocommit=False, use NullPool, bounded connection timeout, and UTC offset-bearing timestamp text.

**Rationale**: [SQLAlchemy SQLite documentation](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) describes legacy versus modern transaction control, SQLite's lack of native datetime types, connection pooling defaults and dialect-specific UPSERT. Explicit timestamp text and NullPool are design choices inferred for this small boundary: they preserve time semantics and avoid retaining idle connections. No WAL requirement is introduced.

**Alternatives considered**: naive datetimes lose offset semantics; retained sessions complicate reader lifetimes; SQL dialect UPSERT reduces portability.

## R4 — Durable schema and safe errors

**Decision**: Version schema explicitly; initialize new storage and validate existing storage without reset. Reconstruct each record through its domain model. Distinguish availability from corruption using driver codes/types, with fixed safe diagnostics.

**Rationale**: Unknown identity and failed lookup must stay distinct. Existing ImportStateUnavailable/Corrupt and E5 already define retryability and privacy. No database exception should cross the boundary.

**Alternatives considered**: silently rebuild broken state, return None on exceptions, map every OperationalError to transient; these conceal loss or endlessly retry invalid state.

## R5 — Integration scope and force

**Decision**: Extend only the existing test Pipeline's run argument and shared decision. Compose real SQLite state, LocalRawArchive and archive replay with a counted fake memory store.

**Rationale**: tests/integration/pipeline.py explicitly reserves production orchestration for #19. It already archives before retain and records failures. Force must reapply sanitization from originals. Counting calls proves extraction avoidance; counting final bank documents does not.

**Alternatives considered**: implement #19 here or defer inherited acceptance tests; neither satisfies this issue's bounded scope.

## R6 — Failure window and retention

**Decision**: State is current outcome, not audit history. No deletion API, export reconciliation or cross-store transaction. A failed forced attempt overwrites success with FAILED and is retried next run.

**Rationale**: ADR-006 forbids deriving deletion from absence. Retain and local commit cannot be atomic; safe resending with stable document identity is preferable to false success. Extraction can repeat after a partial failure and this limitation is explicit.

**Alternatives considered**: mark success before retain (silently loses failed work), retain old success after a failed force (can suppress needed retry), infer deletion from exports (forbidden).

## Research completion

Repository research was delegated to a read-only research agent as required by speckit-plan. Findings were checked against the interface, existing harness and canonical model. No unresolved design questions or extension hooks remain. External references describe library mechanics; project policy comes from the local constitution and ADRs.
