# Feature Specification: Conversation-by-conversation ingestion

**Feature Branch**: `018-ingestion-pipeline`
**Created**: 2026-10-31
**Status**: Implemented — ready for pull request review
**Input**: Issue #19, Compose the ingestion pipeline conversation by conversation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import despite an individual failure (Priority: P1)

An operator imports an export and receives a trustworthy outcome for each conversation even when one conversation is broken.

**Why this priority**: One broken conversation must not block the remaining history.
**Independent Test**: Import three synthetic conversations with a failure in the middle; the first and last are imported and the middle failure is reported with identity, safe error and time.

**Acceptance Scenarios**:

1. **Given** valid conversations around a malformed one, **When** import runs, **Then** both valid conversations finish and the malformed one is failed.
2. **Given** a failure during processing or storage, **When** the next conversation is available, **Then** it is attempted independently.
3. **Given** an empty export, **When** import runs, **Then** the report has zero outcomes and successful completion.

### User Story 2 - Resume without repeated extraction (Priority: P2)

An operator repeats an import and only new, changed or previously failed conversations are processed.

**Why this priority**: Resuming must preserve progress and avoid repeated extraction costs.
**Independent Test**: Repeat an import; unchanged successful conversations are skipped without downstream processing or writes.

**Acceptance Scenarios**:

1. **Given** a successful unchanged conversation, **When** import repeats, **Then** it is skipped and its successful state is preserved.
2. **Given** changed content or a previous failure, **When** import repeats, **Then** processing is attempted.
3. **Given** explicit force, **When** import repeats, **Then** unchanged conversations are reprocessed from originals with stable identity.

### User Story 3 - Preserve safe, traceable history (Priority: P1)

An operator can trace each retained conversation to an archived original and a sanitized normalized form with original time and provenance.

**Why this priority**: Retained history must be recoverable and safe to retrieve.
**Independent Test**: Inspect the archive and retained synthetic conversation and verify secret redaction, metadata and write order.

**Acceptance Scenarios**:

1. **Given** a conversation containing a synthetic secret, **When** imported, **Then** only sanitized content reaches memory and the normalized archive, while original bytes are preserved locally.
2. **Given** an archive write failure, **When** processing continues, **Then** that conversation is never retained.
3. **Given** no matching project, **When** imported, **Then** the conversation is retained with the unknown project and its original identity and time.

### Edge Cases

- Recoverable parser failures may lack a usable native id; report unknown identity explicitly without inventing a persistent document id.
- An unreadable export or unrecoverable iterator failure ends reading with a run-level error and preserves prior outcomes.
- State read failure prevents retain for that item; state write failure after retain remains failed and can be retried safely.
- Failure recording can itself fail; retain both safe diagnostics in the run report and continue.
- All skipped is successful; all failed is total failure; some imported or skipped plus any failure is partial success.
- Interrupts and process termination propagate; the pipeline does not swallow cancellation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Process conversations independently through parsing/normalization, sanitization, classification, enrichment, archiving and retention in that order.
- **FR-002**: Consult import state using source identity and the content hash as read before downstream processing; skip only unchanged successful imports unless forced.
- **FR-003**: Archive original bytes and sanitized enriched normalized content before retention. Archive failure MUST prevent retention.
- **FR-004**: Preserve deterministic document identity and original conversation timestamps; attach source, source id, project, repository when known, importer version and convention-compliant tags.
- **FR-005**: Report exactly one imported, skipped or failed outcome for each encountered conversation; include safe error and UTC failure time for failures and native identity when available.
- **FR-006**: Persist successful state only after retention succeeds; persist identified failures when enough identity and content information exists. Never overwrite successful state with a skip.
- **FR-007**: Continue after individual failures, including recoverable source errors; expose terminal source failures separately without losing earlier outcomes.
- **FR-008**: Distinguish success, partial success and total failure in the returned result for later command-line integration.
- **FR-009**: Keep diagnostic content free of conversation text, credentials and raw exception messages that may expose them.
- **FR-010**: Compose replaceable boundaries without referencing a specific memory engine or concrete storage adapter.

### Key Entities

- **Conversation outcome**: Source identity when known, stable document id when known, outcome, completion time and safe failure description.
- **Run report**: Ordered outcomes, imported/skipped/failed totals, optional terminal error and aggregate completion status.
- **Import record**: Existing successful or failed state for a source/native id, retaining the pre-sanitization content hash.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A three-conversation fixture with a broken middle item imports both valid items and reports exactly one failure with available identity, safe error and time.
- **SC-002**: An unchanged second import performs zero extraction calls and preserves successful state for every skipped item.
- **SC-003**: Every retained fixture has both archived forms before extraction, stable identity, original time and complete provenance.
- **SC-004**: Synthetic secret sentinels appear in neither retained content nor normalized archive nor diagnostics.
- **SC-005**: Empty, all-skipped, partial-failure and all-failed runs produce unambiguous aggregate outcomes with reconciled counts.

## Assumptions

- Scope is Phase 1 MVP orchestration only; source adapters already parse and normalize. No new history source, CLI command, queue, worker or bank provisioning is added.
- Dependencies #10, #11, #12, #13, #14 and #16 supply the existing boundaries and adapters; this feature composes them.
- Execution is synchronous and sequential, with one import-state writer. Adapter-owned retries are reused without a second pipeline retry loop.
- Force is exposed by the pipeline; CLI flags and numeric exit-code mapping belong to #21.
- Default enrichment supplies source, project and conversation type tags; optional user/repository metadata is supplied explicitly when known. No project or repository is inferred a second time.
- No clarification question is needed: scope, identity, error handling, security and outcomes are settled by existing contracts and these recorded assumptions.
