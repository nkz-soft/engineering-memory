# Feature Specification — Import Health and Project-Model Freshness

**Feature Branch** `041-import-health-model-freshness`
**Created** 2026-11-19
**Status** Draft for review
**Input** [Issue #87](https://github.com/nkz-soft/engineering-memory/issues/87), step 6 of roadmap #81

## User Scenarios & Testing

### User Story 1 — Diagnose a missing import (P1)

An operator opens Status in the local explorer to see which source is healthy, failed, or waiting, even after the importer and explorer have restarted.

1. Given one source completed a successful import and another encountered a source error, reopening the explorer after restart shows the successful import time and the other source's safe error category.
2. Given a source succeeds and later fails, the view shows the latest failure alongside the prior successful import time. A subsequent healthy check clears the active failure.
3. Given a configured session source with only deferred sessions, the view shows waiting. Given a source with no recorded outcome, the view shows that no outcome is available.

### User Story 2 — Check freshness for a project (P2)

An operator selects the same project scope used in the explorer and checks the refresh and freshness state for its architecture, stack and decisions models.

1. Given a completed model and a confirmed later import in that project, the model shows stale, even if the conversation itself is old.
2. Given missing or incomparable freshness evidence, the model shows unknown. A later import in a different project never makes this project stale.
3. Given a previously refreshed model and a subsequent failed refresh, the operator can see both the last completed refresh and the newer failure. Source status remains visible when model metadata is unavailable.

### Edge Cases

- Partial imports show a partial outcome and may advance the successful import time if at least one conversation was successfully committed. A no-op scan, an unchanged replay and a dry run do not advance it.
- Existing installations and fresh installs show an explicit absence of recorded status when evidence is missing. A failure to read status storage is visible as unavailable.
- A source can have deferred sessions while also importing other sessions. Deferred work is visible independently of the latest outcome.
- Missing, pending and failed model refreshes are distinct from unknown freshness. A completed model's content is unnecessary for checking status.

## Requirements

### Functional Requirements

- **FR-001** The authenticated explorer MUST expose a read-only Status view with one row per supported import source, the most recent observed outcome, and the last successful import time when known.
- **FR-002** The system MUST persist source outcomes and successful import times locally and preserve them across importer and explorer restarts. A failed attempt MUST preserve prior success, and a newer clean attempt MUST clear earlier error categories.
- **FR-003** The status MUST report automatic session imports and ordinary imports, including archive replay and import paths reused by setup and acquisition. Dry runs and invocations that never attempt a source MUST leave source status alone.
- **FR-004** Status MUST distinguish healthy checks, failures, partial completion, deferred work and absence of recorded outcomes. Categories MUST come from a fixed vocabulary.
- **FR-005** For the selected project, Status MUST display refresh state, last completed refresh time and last known refresh failure time when available for each supported model kind.
- **FR-006** The system MUST show stale when reliable evidence establishes that relevant imported data is newer than the model, or the model service explicitly reports it stale. It MUST show unknown when freshness evidence is insufficient and show current only on affirmative freshness evidence. Imports in other projects MUST have no effect on the local comparison.
- **FR-007** Status storage and display MUST use a closed set of operational fields. They MUST exclude credentials, authorization headers, exception text, paths, conversation bodies and identifiers, hashes, model content and evidence references.
- **FR-008** Status reads MUST preserve the explorer's existing local authentication and project selection. They MUST leave imports and models untouched and preserve available source status if the model service is unavailable.

### Key Entities

- **Source health** holds the latest observed attempt state and category values for a supported source, alongside its independently tracked last successful import time.
- **Project import evidence** records the most recent confirmed import for a classified project.
- **Model health** pairs project and model kind with refresh metadata and the derived freshness state.

## Success Criteria

### Measurable Outcomes

- **SC-001** After restarting both processes, a synthetic healthy source and failed source still show distinct outcomes, and a failure following success preserves the exact prior success time.
- **SC-002** In a fixture with a demonstrably older model, a model with missing evidence and an unrelated project import, all three resolve according to FR-006.
- **SC-003** Zero credential, conversation and model-content sentinel values appear in the status metadata store, response or view during successful, partial, failed and unavailable scenarios.
- **SC-004** Operators can reach the status view from the unlocked explorer alone and identify source outcomes and scoped model state without consulting import logs.

## Assumptions

- Extend the existing loopback explorer (#84) and include the four supported ingestion sources. Automatic scans (#83) supply waiting evidence. This feature does not inspect native session trees or schedules to predict pending work.
- Last successful import means the last confirmed import of a conversation, even within a partial run. A clean no-op shows a healthy check without changing that timestamp.
- Installed histories have no reliable per-source run ledger or project import watermark. Keep pre-upgrade status unknown wherever evidence is insufficient. Freshness is project-wide across its three model kinds and compares import time, not conversation time.
- Status is refreshed on demand and has no controls that initiate imports or refreshes. Existing CLI and MCP contracts remain compatible.
