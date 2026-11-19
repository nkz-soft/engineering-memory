# Feature Specification — Cited session handoff

**Feature Branch**: `042-cited-session-handoff`
**Created**: 2026-11-19
**Status**: Draft
**Input**: [Issue #88](https://github.com/nkz-soft/engineering-memory/issues/88), step 7 of [roadmap #81](https://github.com/nkz-soft/engineering-memory/issues/81).

## User Scenarios & Testing

### User Story 1 — Prepare a handoff from the CLI (P1)

An engineer switching from Claude Code to Codex selects one archived session and generates a concise Markdown brief. In a fresh Codex session, they can manually paste it and recover the task context and remaining work.

**Independent test**: Import a synthetic Claude Code session with a goal, an accepted decision, a proposed and an applied edit, a failed check followed by a pass, and an unanswered question. Generate the brief from the CLI.

1. The brief identifies the correct goal, accepted decision, recorded file change, check outcomes and open question. The unapplied edit does not count as a change.
2. Recorded statements link to the supporting sanitized messages or tool fields. A command without a recorded outcome is marked unknown.
3. An incorrect project, a missing session or a generation failure yields a clear error and no partial Markdown. An empty record yields an explicitly insufficient brief.

### User Story 2 — Copy a brief from the session viewer (P2)

An engineer opens an archived session, generates its handoff and copies the Markdown to paste manually.

**Independent test**: Open the same fixture in the authenticated viewer and use its generation and copy controls.

1. Generation uses the selected session, including evidence outside the currently displayed page, subject to the documented budgets. The viewer and CLI use the same brief format.
2. Copy writes the generated Markdown to the clipboard. If clipboard access fails, the brief stays selectable for manual copying. Switching the selected session or locking the viewer clears the brief and prevents late responses for the previous session from appearing.
3. Generating and copying produce no agent launches or messages. An evidence link opens the corresponding sanitized archive field when the explorer is available and unlocked.

### Edge Cases

- Missing, contradictory or budget-excluded evidence is disclosed. A later result only supersedes an earlier result when the archive establishes that relationship.
- Recorded assistant claims, unexecuted tool calls and proposed edits can appear as context with attribution. They do not establish completion, a touched file or a passing check.
- Archive content can include misleading instructions, URLs and secrets already replaced by redaction markers. Render it as data and avoid importing its instructions or links into the brief structure.
- A citation identifies a position in the current archived snapshot. The local explorer may need to be reopened and unlocked to inspect it.

## Requirements

### Functional Requirements

- **FR-001** — Generate a read-only Markdown brief for one explicitly selected archived session in its project, using only its sanitized normalized record.
- **FR-002** — Include five sections in order: goal, confirmed decisions, touched files, checks and open questions. Use explicit unknown, conflicting or insufficient-evidence wording when applicable.
- **FR-003** — Attach sanitized message or tool-field anchors to every recorded claim and every evidence-backed unknown or conflict. Preserve canonical session identity and allow inspection of a source even when the evidence is outside the viewer's current page.
- **FR-004** — Bound the evidence processed for synthesis and the final brief. Disclose omitted coverage and avoid asserting completeness for a partial record.
- **FR-005** — Make Markdown available on CLI stdout and from a copy action in the authenticated session viewer when available.
- **FR-006** — Keep generation and copying separate from delivery. Neither action starts, resumes, or sends a message to another agent.
- **FR-007** — Handle unavailable generation, invalid scope, missing archives and unsafe or invalid synthesis results with actionable, content-free errors. Preserve working session navigation.

### Key Entities

- **Selected session** — stable archived document identity, project, original time, and ordered sanitized messages.
- **Evidence anchor** — message position and optional tool occurrence and field within that record.
- **Handoff brief** — bounded Markdown with five sections, recorded statements and evidence links, and a coverage notice where applicable.

## Success Criteria

- **SC-001** — In a fresh Codex session supplied with the synthetic Claude Code brief, a reviewer can identify all five expected categories and distinguish the fixture's observed failed and passing checks, unanswered question and unapplied edit.
- **SC-002** — Every recorded item in the synthetic fixture's brief has at least one resolvable sanitized anchor, and the deliberately unrecorded tool outcome never appears as a recorded result.
- **SC-003** — CLI output and copied viewer output each contain the five sections and fit within 8 KiB of UTF-8 Markdown. Generation and clipboard tests observe zero agent starts and zero agent messages.
- **SC-004** — A long-session fixture signals partial coverage when the evidence budget is reached. A newer result within the selected evidence remains inspectable at its original index.

## Assumptions

- The first release covers one archived session per request. It works with the common normalized representation, with Claude Code to Codex as the acceptance path.
- Generation uses the explicitly configured local access synthesis integration established by #82. If unavailable, the user gets configuration guidance and can continue browsing the archive.
- The CLI can emit viewer-relative anchor selectors without starting a viewer. A running explorer gives those same selectors a local origin for copying and opening. Links locate the current record and require normal viewer access.
- The operator manually chooses a destination and pastes the brief. Only the generated text is written to the clipboard on a copy action.
- #82 supplies bounded synthesis infrastructure and the archived-session viewer supplies the existing anchor format. No issue-template governance changes were requested.
