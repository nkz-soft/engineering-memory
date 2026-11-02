# Feature Specification: Claude Code session history

**Feature Branch**: `026-claude-code-source`
**Created**: 2026-11-02
**Status**: Draft — ready for planning review
**Input**: Issue #27, Add Claude Code sessions as a history source, tool calls included.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recover the debugging chain (Priority: P1)

As an engineer, I can import a saved coding session and recall why a command failed,
what investigation followed, and which change fixed it.

**Why this priority**: A conclusion without the command and error loses the engineering evidence.
**Independent Test**: Import a synthetic session with a failed command, investigation and fix;
recall its distinctive root cause and open the sanitized conversation.

**Acceptance Scenarios**:

1. **Given** a session with interleaved prose, calls, outputs and diffs, **When** imported,
   **Then** the original sequence, command arguments, error output and fix remain retrievable.
2. **Given** parallel calls returning out of order, **When** imported, **Then** each output
   stays associated with its own request, and an unfinished call remains visibly unfinished.
3. **Given** a secret in a command, output or diff, **When** retained or opened through memory
   access, **Then** the value is redacted and the surrounding debugging context remains.

### User Story 2 - Recall by the actual project (Priority: P1)

As an engineer, I can find a session by the project recorded in its repository context,
even when its prose names a different project.

**Why this priority**: This is the first source with explicit project context under architecture §15.
**Independent Test**: Import a synthetic session with working directory `/work/orchard` and
prose naming another project, then inspect provenance and scoped recall.

**Acceptance Scenarios**:

1. **Given** usable repository or working-directory metadata, **When** classified, **Then**
   that metadata determines a real project ahead of prose aliases.
2. **Given** no usable context, **When** classified, **Then** existing alias rules apply,
   falling back to `project:unknown` only when neither level resolves.
3. **Given** sessions from different sources with the same native id, **When** imported,
   **Then** their identities and source-scoped retrieval remain distinct.

### User Story 3 - Replay safely and incrementally (Priority: P2)

As an operator, I can import a selected snapshot, repeat it without paying for unchanged
content, and rebuild from the raw archive without the original session directory.

**Why this priority**: The archive is the source of truth; repeatable imports are mandatory.
**Independent Test**: Import twice, change an output, and replay after removing the input snapshot.

**Acceptance Scenarios**:

1. **Given** unchanged session bytes, **When** reimported, **Then** no second extraction occurs.
2. **Given** a changed tool output, **When** reimported, **Then** the same document is updated.
3. **Given** a malformed session beside a valid session, **When** imported, **Then** the failed
   session is reported without content disclosure and the valid session still imports.
4. **Given** archived originals alone, **When** replayed, **Then** parsing reconstructs the
   ordered session and repository context with the same identity.

### Edge Cases

- Empty snapshots; blank lines; invalid JSON or incomplete final lines; missing native id/time.
- Duplicate record ids, conflicting session ids, parent branches and sidechain records.
- Multiple tool calls, orphan results, missing results, error flags and nested result blocks.
- Unknown metadata events, non-text attachments and references to external tool-output files.
- Windows/POSIX paths, trailing separators, repository URL credentials and missing context.
- Session working directory changes; context-only corrections; partial or actively changing files.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Operators MUST explicitly select Claude Code for a saved session file or directory
  snapshot; existing source defaults MUST remain compatible.
- **FR-002**: Sessions MUST use native session ids, `claude-code:{session-id}` document ids,
  source timestamps and `source:claude-code` tags. Import time MUST NOT replace source time.
- **FR-003**: Normalization MUST preserve ordered prose, tool requests, outputs, error status,
  call/result association and textual diffs, including mixed blocks in a single turn.
- **FR-004**: Missing results MUST NOT be invented. Unsupported/non-text content MUST be marked
  and retained in the original, without executing tools or following external file references.
- **FR-005**: Repository or working-directory context MUST resolve a deterministic project before
  prose rules; known repository provenance MUST accompany retained items.
- **FR-006**: Original session bytes and sanitized normalized content MUST use the existing raw
  archive, and replay MUST reparse the originals without consulting a live repository.
- **FR-007**: Existing sanitization MUST cover all newly introduced textual fields before retention
  or sanitized access; diagnostics MUST NOT contain session content or credentials.
- **FR-008**: Reimport MUST skip unchanged content and update changed debugging content under the
  same identity; existing sources MUST NOT incur a hash migration merely because this source exists.
- **FR-009**: A bad session MUST fail as one conversation without aborting subsequent sessions.
- **FR-010**: Dry-run, force and archive replay MUST work through the existing import workflow.
- **FR-011**: This source MUST have its own ADR and specification; bank, tags and memory-engine
  contract MUST retain their existing meaning.

### Key Entities *(include if feature involves data)*

- **Session**: Native id, source times, repository context and ordered turns.
- **Tool activity**: Tool name, native association, request, output and failure/incomplete status.
- **Source context**: Repository or working directory carried by the snapshot, used for provenance
  and deterministic project selection independently of conversational prose.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A root-cause recall returns the synthetic debugging session, and opening it exposes
  all four steps: failed command, error, investigation and solution.
- **SC-002**: Every fixture with usable explicit repository context receives the expected real
  project; conflicting prose never overrides it.
- **SC-003**: An unchanged second import makes zero extraction calls; a changed output updates
  exactly the existing document; archived-only replay preserves identity and evidence.
- **SC-004**: No planted secret value reaches retained or access-served content or diagnostics.
- **SC-005**: A malformed session does not prevent the following valid fixture from importing.

## Assumptions

- #19's shared ingestion pipeline is available on main. Phase 2 coding-agent sources are in scope.
- Input is an operator-provided, quiescent UTF-8 JSONL snapshot, not a watcher or acquisition service.
- One top-level session file represents one conversation. Directory discovery excludes nested
  subagent/sidechain files; inline sidechain records are preserved only in originals and marked.
- Preserve main-session record/block order rather than guessing a new branch traversal. Explicitly
  reject duplicate conversational record ids or conflicting native session ids.
- Derive a project slug from explicit repository basename, otherwise working-directory basename;
  configured aliases can map that metadata to an established project before basename fallback.
- First usable repository context in record order is authoritative for a session. Later cwd changes
  do not silently reassign it. No probing the current filesystem or git remotes.
- Context-only corrections follow existing metadata skip behavior: force/replay is needed to refresh
  retained provenance; they do not change the global content hash contract.
- Truncated inputs fail the session; external tool-output files, binary attachments, live acquisition,
  Codex/Hermes sources and consumer configuration are separate work.
- Clarification review found no blocking ambiguity; these assumptions are reviewable at the gate.
