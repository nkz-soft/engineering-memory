# Feature Specification: Local Raw Archive

**Feature Branch**: `012-local-raw-archive`

**Created**: 2026-10-26

**Status**: Draft — awaiting planning review

**Input**: [Issue #13](https://github.com/nkz-soft/engineering-memory/issues/13), "Persist originals and normalized forms in a local raw archive". Preserve both forms independently of extracted memory, enumerate by stable identity, and replay ingestion without the source export.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Keep a durable source of truth (Priority: P1)

An operator imports history and can retrieve its exact original payload and sanitized normalized conversation after the importing process exits.

**Why this priority**: Extracted memory is lossy; losing either archived form defeats recovery and inspection.

**Independent Test**: Store a conversation using every supported field, reopen the archive, and compare both forms and the content hash to their inputs.

**Acceptance Scenarios**:

1. **Given** an empty archive, **When** both forms are stored successfully and the archive is reopened, **Then** the normalized form, hash, original bytes, and media type equal their inputs.
2. **Given** an archived conversation, **When** the same identity is stored again with changed content, **Then** there is one current document and both forms belong to the replacement.
3. **Given** an existing document, **When** its replacement fails before publication, **Then** the previous complete pair remains readable.
4. **Given** an unknown identity, **When** either form is requested, **Then** a declared permanent missing-document failure is reported.

### User Story 2 - Replay without another export (Priority: P1)

An operator reprocesses archived originals when parsing, redaction, or classification rules change, without requesting another source export.

**Why this priority**: Recovery must correct old processing decisions rather than reproduce them from saved normalized forms.

**Independent Test**: Import synthetic ChatGPT history, delete its export, enumerate a reopened archive, and run parsing, sanitization, classification, enrichment, archiving, and retention from originals using fresh import state.

**Acceptance Scenarios**:

1. **Given** several archived conversations and no export, **When** enumeration runs, **Then** each current document is discoverable exactly once and readable by stable identity.
2. **Given** originals saved with normalized forms reflecting older processing, **When** replay runs with current rules, **Then** current parsing, sanitization, and classification are applied to originals.
3. **Given** an unreadable original followed by a valid one, **When** replay runs, **Then** the failure is attributed to its document and the valid one can still be processed.
4. **Given** an empty archive, **When** enumeration or replay runs, **Then** it completes with no conversations and no failure.

### User Story 3 - Replace storage without changing ingestion (Priority: P2)

A maintainer substitutes an in-memory implementation and exercises identical archive behavior through the shared boundary.

**Why this priority**: Ingestion must remain independent of storage layout and any future object store.

**Independent Test**: Run the reusable archive contract against both implementations, with local durability verified by a fresh instance over the same directory.

**Acceptance Scenarios**:

1. **Given** either implementation, **When** shared round-trip, replacement, lookup, enumeration, and failure contracts run, **Then** both provide the same observable semantics.
2. **Given** unavailable storage or a corrupt record, **When** a caller reads or writes, **Then** only declared boundary failures escape and diagnostics contain no payload content.

### Edge Cases

- Native IDs containing slashes, colons, Unicode, reserved filenames, or traversal-like text must not escape the archive or collide.
- Empty and arbitrary binary originals round-trip unchanged.
- Interrupted initial writes expose no partial record; interrupted replacements preserve the previous complete pair.
- Malformed data, unknown storage versions, mismatched identities, and missing halves fail explicitly.
- Unreadable/unwritable storage and full disks report availability failures.
- Independent readers can inspect complete committed records during import; enumeration need not provide a transaction-wide snapshot of concurrent changes.
- Missing conversations in later exports never cause deletion.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Persist original payload and sanitized normalized form together for each source and native identifier, independently of extracted memory.
- **FR-002**: Successful writes MUST survive reopening with every normalized field, hash, original byte, and media type unchanged.
- **FR-003**: Stores MUST be idempotent by stable identity; the last successful store replaces both forms and leaves one discoverable document.
- **FR-004**: Publication MUST expose complete pairs only. Failed unpublished replacement MUST preserve the previous complete pair.
- **FR-005**: Callers MUST retrieve either form by identity and enumerate all current identities without consulting exports, import state, or extracted memory.
- **FR-006**: Enumeration MUST support processing one conversation at a time without materializing all conversation bodies.
- **FR-007**: Replay MUST reparse originals and run current downstream processing through existing boundaries, rather than substituting saved normalized content.
- **FR-008**: Replay MUST preserve source identity and real timestamps and allow later documents to be processed after a document-specific failure.
- **FR-009**: Missing documents, invalid records, unsupported versions, and unavailable storage MUST produce explicit permanent or retryable boundary failures. Library exceptions and payload content MUST NOT appear in public diagnostics.
- **FR-010**: Opaque identifiers MUST round-trip unchanged without selecting paths outside the root or overwriting another identity.
- **FR-011**: Local and in-memory storage MUST pass the same reusable contract; local durability MUST additionally be tested with a fresh instance.
- **FR-012**: Originals MUST stay local and MUST NOT be logged or served to consumers. Only sanitized normalized content is eligible for consumer reads and retention.
- **FR-013**: Archive writes MUST complete before retention. Export absence MUST NOT trigger archive deletion.

### Key Entities *(include if feature involves data)*

- **Document identity**: Source plus native identifier, deterministic and stable across imports.
- **Original payload**: Exact per-conversation bytes and media type supplied by the source, sufficient for parsing again.
- **Normalized form**: Sanitized conversation, provenance, project classification, tags, real timestamps, and content hash.
- **Archive record**: One complete current pair with format metadata sufficient to validate and reopen it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every field and original byte in the synthetic round-trip corpus survives reopening with zero differences.
- **SC-002**: Shared archive behavior passes for both implementations, and a fresh local instance demonstrates durability.
- **SC-003**: After export deletion, full replay processes every valid archived conversation, preserves identity and real timestamps, and retains content sanitized under current rules.
- **SC-004**: Injected publication failures expose no mixed pair, and failed replacement leaves the previous record readable.
- **SC-005**: Empty, repeated, and multi-document imports enumerate zero, one per identity, and all committed identities respectively; hostile IDs create no files outside the root.

## Assumptions

- Scope is Phase 1 MVP, architecture §§14 and 21–22. This adds persistence and a replay source, not production orchestration or a new CLI command.
- Issue #9 supplied the boundary (feature 007). Existing parsing, sanitization, and classification are reused.
- One importer writes a root at a time; independent local consumer processes may read concurrently. Distributed writers and network filesystems are outside MVP scope.
- Last successful write wins; historical revisions and garbage collection APIs are outside scope. No export-based deletion (ADR-006).
- Replay with changed rules uses fresh import state. Broader reprocess policy belongs to #19. Acceptance uses the existing test pipeline and fake memory/state, without requiring a live service.
- Originals preserve per-conversation records, not the surrounding export or ZIP byte-for-byte. Originals remain unsanitized locally; callers sanitize normalized forms before storing.
- Unsupported future formats fail explicitly; no speculative migrations or new history sources.
- No critical ambiguity remains beyond these recorded assumptions; no governance-impact box is selected in the issue.
