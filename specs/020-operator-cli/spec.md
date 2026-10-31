# Feature Specification: Operator command line

**Feature Branch**: `020-operator-cli`
**Created**: 2026-10-31
**Status**: Draft — awaiting human planning review
**Input**: Issue #21: expose provisioning, export/archive import, and import status.

## User Scenarios & Testing

### User Story 1 - Prepare the bank (Priority: P1)

An operator prepares the shared bank and verifies the configured retain mission before importing history.

**Why this priority**: Import requires an explicitly provisioned bank.
**Independent Test**: Provision a scratch instance twice; verify the mission both times.

**Acceptance Scenarios**:
1. Given a reachable instance, when provisioning runs, then the mission is applied and verified and the command succeeds.
2. Given invalid configuration or an unavailable instance, when provisioning runs, then a safe diagnostic and nonzero exit identify failure.

### User Story 2 - Import and replay history (Priority: P1)

An operator imports a ChatGPT export or reprocesses originals from the raw archive and sees imported, skipped and failed counts.

**Why this priority**: This makes the existing pipeline usable without writing Python.
**Independent Test**: Import synthetic history, repeat unchanged, change one conversation, and replay the archive with explicit force.

**Acceptance Scenarios**:
1. Given valid history, when imported, then originals and sanitized normalized forms are archived before retention and outcomes are reported.
2. Given unchanged imported history, when repeated, then it is skipped without additional extraction; changed or failed items are attempted.
3. Given an archived original and no export, when replay is requested, then the existing pipeline reconstructs the conversation without requiring a new export.
4. Given one malformed conversation, when a later valid conversation exists, then processing continues and the overall command exits nonzero.
5. Given force is requested, when unchanged history is read, then it is reprocessed under current rules using stable identity.

### User Story 3 - Inspect import state and script commands (Priority: P2)

An operator inspects the latest remembered outcomes without contacting the memory engine. Scripts request structured results instead of parsing prose.

**Why this priority**: Status and stable output make failures actionable.
**Independent Test**: Query synthetic persistent state offline; compare text and structured output with an import run report.

**Acceptance Scenarios**:
1. Given remembered successes and failures, when status runs, then each latest record and aggregate counts are shown.
2. Given an unchanged re-import, when its run report shows skips, then status still describes the last persisted imported result and does not invent skip history.
3. Given any operational command with structured output selected, when it completes or fails, then stdout contains exactly one machine-readable result and no progress prose.
4. Given empty state, when status runs, then it reports zero records successfully without creating state.

### Edge Cases

Empty export/archive; missing/unreadable input; corrupt state; source failure after progress; all skipped; mixed results; failure to write state after retention; interrupted run; invalid command combinations; missing configuration; diagnostic messages containing synthetic secrets.

## Requirements

### Functional Requirements

- **FR-001**: Preserve the existing provisioning command and version/help behavior.
- **FR-002**: Expose mutually exclusive export import and archive replay, with explicit force support; reject absent/conflicting source selection before side effects.
- **FR-003**: Reuse existing skip, replay, sanitization, classification, provenance and archive-before-retain rules without redefining them.
- **FR-004**: Report imported/skipped/failed counts, per-item safe outcomes, and terminal source failures; partial success MUST exit nonzero.
- **FR-005**: Report latest persistent import records offline and read-only, with imported/failed totals. Explicitly document that skipped is a run outcome, not stored history.
- **FR-006**: Provide human-readable output by default and an explicit machine-readable option for every operational command, with documented stable field names and exit codes.
- **FR-007**: Configuration and operational errors MUST not print raw exceptions, conversation bodies, titles, credentials or authorization headers. Diagnostics use fixed safe categories and stages.
- **FR-008**: Release resources on success, failure and interruption; maintain sequential single-writer ingestion.
- **FR-009**: Document every command and flag, configuration prerequisites and result semantics in README, with executable fixture and live validation scenarios.
- **FR-010**: Cover every command through its CLI invocation, including failure and structured-output paths, and validate provisioning/import/status against a fixture corpus and a live instance before completion.

### Key Entities

- Command result: command, semantic outcome, safe diagnostics and command-specific data.
- Run report: transient per-conversation outcomes and aggregate counts, including skips.
- Import record: latest persisted outcome per source/native identity; no historical run or skip ledger.

## Success Criteria

- **SC-001**: All three operator workflows complete from documented commands without custom application code.
- **SC-002**: A second unchanged fixture import reports every previously successful item skipped and makes zero additional retention requests.
- **SC-003**: Every tested failure exits nonzero, including mixed runs, and preserves subsequent item processing where supported.
- **SC-004**: Every operational command produces one parseable structured result when requested; fixture secrets appear zero times in stdout/stderr.
- **SC-005**: Offline status agrees exactly with persisted latest outcomes and changes no archive or state files.

## Assumptions

- Dependencies #17, #19 and #39 are merged; ADR-006 governs resync and force semantics.
- Scope is Phase 1 under architecture sections 21–22. No HTTP surface, new source, scheduler, retrieval command or parallel ingestion is added.
- Existing configuration and shared bank policy remain authoritative. Credentials are never CLI arguments.
- Status means latest durable records, not a historical ledger; run skips are visible in the import result only.
- Dry-run is the separate issue #22; this feature does not introduce its flag.
- Empty import/replay is successful with zero counts; status without a database is successful and empty, while corrupt existing state fails.
- An offline status command must not require memory/LLM configuration or construct network clients.

## Clarification Review

Functional scope, entities, interaction, reliability, security, dependencies and measurable outcomes were checked. No unresolved clarification is required; command spelling, result fields and failure codes are fixed in the design contract for review.
