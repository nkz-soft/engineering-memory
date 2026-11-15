# Feature Specification: Automatic Coding-Agent Session Import

**Feature Branch** `037-automatic-session-import`
**Created** 2026-11-15
**Status** Draft
**Input** [Issue #83](https://github.com/nkz-soft/engineering-memory/issues/83)

## User Scenarios & Testing

### User Story 1 - Import configured sessions on demand (P1)

An operator selects local Codex and Claude Code directories and runs one command. Eligible sessions become searchable through the existing read-only memory tools, with their source and original time.

**Independent test** Populate two configured directories with synthetic sessions and put a competing session outside them. Run once, search memory and open the two sanitized source conversations. Confirm the competing session is absent.

1. Given a ready backend and supported, settled sessions, when the operator runs the command, then both sources are processed without manual copying.
2. Given one configured source and one unconfigured source, when the operator runs the command, then only the configured source is read.

### User Story 2 - Keep memory current on an opted-in schedule (P2)

An operator schedules the same command and can disable the schedule without changing stored history.

**Independent test** Schedule the command using a test profile, add a settled session, and verify it is searchable after a scheduled run. Disable the schedule and verify that later files wait for the next explicit run.

1. Given an enabled schedule and a session meeting the eligibility rules, when a scheduled run completes successfully, then the session is searchable.
2. Given an unchanged session and a resumed session with new content, when the next run completes, then only the changed content is extracted and its document keeps the same identity.

### User Story 3 - Diagnose and retry independently (P3)

An operator can tell what each source imported, skipped, deferred or failed and can rerun after a transient problem.

**Independent test** Put a changing file and a malformed settled file alongside a valid file. Run the command, then stabilize or fix the affected files and repeat.

1. Given a file still changing, when it is inspected or copied, then it is deferred and a later run can retry it.
2. Given a malformed or unreadable file, when a source is scanned, then its failure is reflected in the source outcome and other eligible files can still import.
3. Given a source directory that cannot be reached, when both sources are configured, then the other source is still processed and the affected source has an actionable error.

### Edge Cases

- Missing configuration, an empty directory, and no newly eligible files have distinguishable outcomes.
- A source file can disappear, be replaced or resume changing while capture is in progress.
- A file may be quiescent for a while and later resume. New content must be eligible on a later run.
- Overlapping invocations for the same import profile produce a visible busy result without processing the same batch concurrently.
- Discovery stays within approved roots, excludes secondary agent histories and does not follow links or junctions.

## Requirements

### Functional Requirements

- **FR-001** Provide a noninteractive one-shot import command for explicitly configured local Codex and Claude Code roots. Either source can be configured independently.
- **FR-002** Provide opt-in scheduling on the supported Windows and Ubuntu workstation platforms using the same command. Installing or setting up the application must leave scheduling off.
- **FR-003** Capture a stable private snapshot of an eligible main-session file. Defer recent, incomplete or changing files based on the documented eligibility policy and revisit them on subsequent runs.
- **FR-004** Reuse the supported source adapters and shared archive, sanitization, extraction and import-state behavior. Unchanged content must skip extraction and a changed session must retain its document identity and original-time provenance.
- **FR-005** Isolate per-file and per-source failures and report imported, unchanged, deferred and failed counts by source. Provide a machine-readable result and signal failures to the scheduler. Keep raw conversation content and credentials out of reports.
- **FR-006** Leave native histories untouched. Allow retry through the same command and remove temporary copies after normal completion or interruption where possible.
- **FR-007** Reuse the existing readiness and provisioning prerequisites. Imported sessions must be available through the existing read-only search and sanitized conversation tools.

### Key Entities

- **Configured source** identifies an agent and the operator-approved local root for its main-session history.
- **Session snapshot** is a private, stable copy of a candidate file for one import attempt.
- **Source outcome** summarizes the counts and diagnostic categories for one agent in one run.

## Success Criteria

- **SC-001** One successful scheduled run makes one eligible synthetic session per configured agent searchable and its sanitized conversation retrievable, with zero manual copying and zero sessions imported from outside configured roots.
- **SC-002** An unchanged rerun triggers zero extractions. A subsequent content update appears under the original document identity, with no duplicate document.
- **SC-003** In a run with a valid file, a changing file and a malformed file, the valid file imports and both exceptional outcomes appear in the summary. The affected files can import after stabilization or repair.
- **SC-004** Record a schedule enable/disable check on each supported workstation platform and demonstrate that scheduling is inactive by default.

## Assumptions

- The bank is already provisioned and the operator configures the local account, credentials and roots used for scheduled runs.
- The supported native formats are those of the existing adapters. Completion is inferred from a configurable quiet period plus a stable copy since a paused file and a closed session can look alike on disk.
- Initial scope is local workstation capture and recall. No live tailing, new source formats, archive deletion synchronization or automatic scanning of other profiles.
