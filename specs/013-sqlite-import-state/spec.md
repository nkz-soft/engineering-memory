# Feature Specification: Persistent Import State

**Feature Branch**: `013-sqlite-import-state`

**Created**: 2026-10-27

**Status**: Draft — ready for human review

**Input**: [Issue #14](https://github.com/nkz-soft/engineering-memory/issues/14), architecture §17 and ADR-006. Remember import outcomes locally so repeated imports avoid extraction cost, failures can be retried, and deliberate forced re-import remains possible.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Refresh without paying twice (Priority: P1)

As the history owner, I can refresh after restarting and pay only for new or changed conversations.

**Why this priority**: Avoiding repeated extraction is the purpose of import state.

**Independent Test**: Import synthetic conversations, reopen state and repeat while counting memory writes.

**Acceptance Scenarios**:

1. **Given** a successful import, **When** the same conversation is imported after reopening state, **Then** no memory write occurs and the run reports skipped.
2. **Given** that success, **When** one message character changes, **Then** the conversation is imported again with the same document identity.
3. **Given** three unchanged refreshes, **When** their outcomes are checked, **Then** all were skipped and the original success record is unchanged.
4. **Given** unchanged messages, **When** only the title or importer metadata changes, **Then** ordinary refresh skips extraction.
5. **Given** two sources using one native identifier, **When** their records are written, **Then** each has an independent outcome.

---

### User Story 2 - Resume failed work (Priority: P1)

As the history owner, I can see which conversation failed and rerun without losing work.

**Why this priority**: Failure must never qualify a conversation for skipping.

**Independent Test**: Fail one memory write, reopen state and rerun with a working store.

**Acceptance Scenarios**:

1. **Given** a failed attempt, **When** state is reopened, **Then** its source identity, content fingerprint, document identity, time, failed status and safe error survive.
2. **Given** that failed record, **When** identical content is imported again, **Then** memory is called and success replaces failure.
3. **Given** one failed conversation, **When** more are available, **Then** later conversations still proceed.
4. **Given** unreadable state, **When** lookup fails, **Then** the conversation is reported failed with no memory write; an error is never treated as an unknown identity.

---

### User Story 3 - Reapply processing deliberately (Priority: P2)

As the history owner, I can force unchanged history through processing after rules change.

**Why this priority**: ADR-006 excludes importer metadata from the fingerprint but promises reprocessing from originals.

**Independent Test**: Ordinary archived replay skips; explicit force re-sanitizes and retains the same conversation.

**Acceptance Scenarios**:

1. **Given** unchanged successful content, **When** force is enabled, **Then** processing and memory retention repeat using the existing document identity.
2. **Given** a failed forced import, **When** ordinary refresh follows, **Then** that conversation is retried.
3. **Given** force is omitted, **When** unchanged content is replayed, **Then** ordinary skip behavior remains the default.

---

### User Story 4 - Keep history missing from a later export (Priority: P2)

As the history owner, I retain previously imported conversations even when a newer export is partial.

**Why this priority**: Absence cannot establish deletion; the archive is independent of the source service.

**Independent Test**: Import two conversations, then refresh with one and with none; inspect archive, state and retained contents.

**Acceptance Scenarios**:

1. **Given** two imported conversations, **When** a later export omits one, **Then** it remains unchanged in archive, state and bank.
2. **Given** an empty later export, **When** import runs, **Then** no stored conversation is removed or removal inferred.

### Edge Cases

- Opaque native identifiers include punctuation, Unicode and SQL-like text without collision or interpretation.
- Message order and message timestamp changes count as content changes; presentation-only changes do not.
- State recording fails after retention: report failure; later retention may repeat using the stable document identity.
- Busy/locked databases, invalid database files, incompatible schemas and malformed records produce safe explicit errors.
- Interrupted replacement exposes a complete prior or new record, never a partial outcome.
- Recorded times preserve their instant and microseconds across reopening, normalizing offsets to UTC.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Persist one current outcome per `(source, source id)`, including fingerprint, document identity, recorded time, status and optional safe error, across restarts.
- **FR-002**: Last completed write MUST replace the prior outcome atomically; different identities remain independent.
- **FR-003**: Ordinary import MUST skip memory writes only for a successful matching canonical content fingerprint.
- **FR-004**: Fingerprints MUST reuse the existing normalized conversation contract before sanitization; no second hashing policy.
- **FR-005**: Skips MUST be reported without replacing remembered success.
- **FR-006**: Failed attempts MUST be recorded with safe error and time when writable, and remain eligible for retry next run.
- **FR-007**: Explicit force MUST bypass content-match skipping and repeat sanitization, archive publication and retention; ordinary refresh remains the default.
- **FR-008**: Import MUST NOT compare stored identities with export membership or infer removals; missing history remains in archive, state and memory.
- **FR-009**: State access MUST use the established replaceable boundary; callers do not depend on database-library exceptions or dialects.
- **FR-010**: Unknown identity returns no record; inaccessible, unreadable or incompatible storage MUST raise a boundary error.
- **FR-011**: Records contain no conversation bodies or credentials. Diagnostics exclude payload values, SQL parameters and backend error text.
- **FR-012**: Support one importer writer and independent readers, one conversation at a time without corpus loading.
- **FR-013**: Initialize new storage explicitly; never silently reset or destructively migrate incompatible existing storage.

### Key Entities *(include if feature involves data)*

- **Import outcome**: Source/native identity, canonical fingerprint, stable document identity, recorded attempt time, success/failure and safe failure explanation.
- **Refresh decision**: Current content compared to remembered success, with explicit force overriding the skip.
- **Storage format version**: Identifies persistent layout so incompatible storage is rejected without loss.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Three consecutive unchanged refreshes after success cause zero additional memory writes, including after reopening state.
- **SC-002**: One character changed causes exactly one additional memory write with unchanged document identity.
- **SC-003**: Failure survives reopening, next run retries, and a third unchanged run skips after success.
- **SC-004**: Ordinary replay skips; forced replay causes one additional memory write through sanitization.
- **SC-005**: Missing and empty exports preserve all previous archive/bank entries and remembered outcomes.
- **SC-006**: Every reusable import-state contract passes on persistent storage, including reopen and boundary errors.
- **SC-007**: Failed replacement preserves prior complete state; lookup failure causes zero memory writes.

## Assumptions

- Phase 1 MVP and ADR-004 fix SQLAlchemy 2 over SQLite; the plan settles the schema.
- Dependencies #9 and #39 are closed. Canonical model, local archive and archive replay source are on `origin/main` at `d6cf0f3`.
- Single writer and local filesystem; distributed ingestion, network storage and PostgreSQL implementation are outside scope.
- Existing integration harness proves composition until #19 provides production orchestration and CLI. This issue provides a production adapter and reusable force-aware decision.
- Force is an explicit per-run harness option and shared decision argument; future import command wiring belongs to #19.
- Callers supply safe failure explanations under the existing boundary contract; the adapter generates fixed safe diagnostics.
- Next-run retry is included; automatic transient retry/backoff belongs to #20.
- Clarification review found no blocking ambiguity. Lifecycle and crash behavior are resolved in the plan; no unanswered questions remain.
