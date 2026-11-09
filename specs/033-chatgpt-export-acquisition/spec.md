# Feature Specification — ChatGPT export acquisition

**Feature Branch** `033-chatgpt-export-acquisition`
**Created** 2026-11-09
**Status** Draft for planning review
**Input** [Issue #40](https://github.com/nkz-soft/engineering-memory/issues/40)

## User Scenarios & Testing

### User Story 1 — Refresh from a watched folder (P1)

After requesting and downloading a ChatGPT export through the supported flow, an operator saves it to a configured local inbox. A scheduled check archives and imports the export and reports the outcome without further interaction.

**Independent test** Place a synthetic export in the inbox and let one configured check run with an empty archive and a test memory store.

1. Given a complete supported ZIP, the check stores its original bytes before import, runs the existing incremental import and reports the archive's outcome.
2. Given an empty inbox, the check reports that no new export is available. Given a byte-identical export under a new name, it reuses the recorded acquisition and skips completed work.

### User Story 2 — Reject incomplete inputs and recover (P1)

An operator can rely on the previous successful refresh when an acquisition fails.

**Independent test** Present a truncated archive after a successful acquisition and compare the archive, acquisition records and import calls before and after the failure.

1. Given a stable truncated archive or damaged member, the check fails visibly and stops before calling ingestion. The previous successful acquisition and conversation state remain intact.
2. Given an interruption after archive storage, or a failed import of a validated export, the next run can resume from archived bytes. An incomplete import remains distinguishable from a completed one.

### User Story 3 — Use the manual fallback and inspect freshness (P2)

An operator can explicitly acquire a ZIP from disk without starting the watcher. The operator can see the last completed export's production time separately from its import completion time.

**Independent test** Manually acquire a fixture with known production evidence and another without, then inspect text and structured status.

1. Given supported production evidence, status shows its UTC time and evidence quality alongside import completion time.
2. Given missing or ambiguous evidence, status reports production time as unknown. Existing import and archive replay commands retain their supported input forms.

### Edge Cases

- Ignore temporary download filenames. Defer changing or newly observed inbox ZIPs until the next qualifying check.
- Treat a stable invalid ZIP in the dedicated inbox as a failure. Moving it out of the inbox lets the next check proceed.
- If two scheduled invocations overlap, only one may perform acquisition and dispatch import for a given configured store.
- An empty export that passes the format checks is valid. An export with fewer conversations never implies deletion.

## Requirements

### Functional Requirements

- **FR-001** Offer interchangeable manual and local-folder acquisition sources through an `ExportSource` boundary upstream of ingestion.
- **FR-002** Support an opt-in local inbox checked on a configurable schedule after one-time operator setup. Downloading the archive into that inbox is the handoff.
- **FR-003** Confirm a complete supported single-file or split ChatGPT export, including ZIP member integrity and complete conversation files, before any ingestion call or successful acquisition record.
- **FR-004** Store the exact accepted archive bytes in the raw archive and use those same bytes for import and recovery. Keep acquisition metadata separate from the archive bytes.
- **FR-005** Maintain one durable acquisition record per distinct ChatGPT archive, including acquisition origin, archive identity, acquisition time, production time evidence when available and completed ingestion time when successful.
- **FR-006** Report invalid input or acquisition failure with a non-success outcome and stop the current check. Preserve prior acquisitions and conversation state on pre-import failure.
- **FR-007** Resume incomplete imports from the validated archived copy, preserving existing conversation-level identity and deduplication. A completed duplicate must not start another import.
- **FR-008** Extend text and structured status additively with the most recently completed acquisition, production time and evidence quality, and import completion time. Keep pre-existing stores readable.
- **FR-009** Keep the manual import and archive replay paths available. Keep all raw exports private and local. Report outcomes without conversation content, sensitive paths, or download credentials.
- **FR-010** Record the seventh boundary in architecture §8 and the acquisition decision in ADR-007, preserving ADR-006's incremental resync and retention policy.

### Key Entities

- **Export candidate** — A local file offered by the manual source or discovered in the inbox.
- **Archived export** — An immutable, byte-for-byte copy of a validated ZIP, identified by its content digest.
- **Acquisition record** — Provenance and lifecycle metadata for one archived export. Its optional production time is distinct from observed and completed times.

## Success Criteria

- **SC-001** Both acquisition modes pass the same contract checks. A complete watched fixture is imported after setup without a manually entered import command.
- **SC-002** A truncated fixture and a fixture with a corrupt later member each produce zero ingestion calls and leave previous successful state intact.
- **SC-003** Retrying an interrupted acquisition or submitting an identical completed archive leaves one record and one archived ZIP. Completed conversation work is skipped on recovery.
- **SC-004** Text and structured status agree on production and completion times for a known-time fixture and report unknown production time when evidence is absent.
- **SC-005** The manual workflow and acquisition tests run with local fixtures and a test memory store, with no mailbox or ChatGPT network dependency.

## Assumptions

- The local inbox is the watcher option selected from the issue. The operator still requests the export and downloads it into the inbox using the signed-in ChatGPT flow. Mailbox retrieval and signed-in browser automation are outside this delivery.
- One trusted operator configures a dedicated inbox and a local scheduler. A scheduled check has a finite lifetime.
- The source may lack authoritative production metadata. Status distinguishes supported estimates from known timestamps and leaves unresolvable values unknown. It never uses download or import time as production time.
- Acquisition applies to ZIPs. Legacy import of extracted directories and standalone JSON remains available through the existing command.
