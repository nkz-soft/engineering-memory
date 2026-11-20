# Feature Specification: Reviewed project playbooks

**Feature Branch** — `044-project-playbooks`

**Created** — 2026-11-20

**Status** — Draft for review

**Input** — [Issue #90](https://github.com/nkz-soft/engineering-memory/issues/90), step 9 in #81, dependent on #82.

Procedures buried in transcripts are hard to reuse. A reviewed playbook packages an ordered procedure and a traceable example for a specific project.

## User Scenarios & Testing

### User Story 1 — Review and approve a draft (P1)

A local operator submits and reviews a procedure with ordered steps and at least one archived example in the same project. Review lets the operator inspect the exact text and evidence references before taking an explicit approval action.

**Independent test** — Submit a draft with two distinct steps and an example. Verify review shows both in order, ordinary retrieval cannot discover the draft, and explicit approval publishes the reviewed revision.

1. Given a draft, when someone searches or requests it through regular memory access, then its text and draft metadata are absent.
2. Given a reviewed draft, when a different revision is staged before approval, then the attempted approval fails and the operator must review the new revision.
3. Given examples from an unrelated project or absent from the archive, publishing fails with a recovery message.

### User Story 2 — Find an approved procedure and open its example (P1)

An agent lists approved procedures for a project through read-only MCP. An operator browses the same project in the local explorer and opens a procedure and its example in the existing viewer.

**Independent test** — Approve one procedure in each of two projects. List and open the target project's playbook from each surface and follow its reference to the sanitized archive.

1. Given an approved playbook, a matching project can find and open it, including ordered steps and provenance.
2. Given a different project, even a known playbook identifier yields no playbook. A changed or missing example produces a visible unavailable state while leaving the stored provenance intact.

### User Story 3 — Publish a revision without losing history (P2)

The operator stages and approves an update while readers continue to see the previous approval until publication. Readers can open an earlier approved version and see the example references recorded for that version.

**Independent test** — Approve version one with example A, stage an update using example B, then approve it. Verify the default version changes once and that both approved versions retain their own steps and example references.

### Edge Cases

- Approval after a referenced archive snapshot changes requires resubmission and review of the new reference.
- A failed publication leaves the prior approved version and pending draft intact. Concurrent approvals cannot produce two versions for a single draft.
- An example can become unavailable after approval. Its link remains identifiable, and guarded viewer navigation reports the unavailable snapshot.

## Requirements

- **FR-001** — An operator MUST be able to stage and inspect a draft with one classified project, a title, one or more ordered nonblank steps and one or more existing examples in that project.
- **FR-002** — Publication MUST require explicit local approval of the exact draft reviewed, with source identity and reviewed snapshot checked at approval.
- **FR-003** — Pending drafts MUST be absent from ordinary search, synthesis, project browsing and approved playbook reads.
- **FR-004** — The read-only MCP and authenticated local explorer MUST list and retrieve approved playbooks by exact project, defaulting to the latest approved version and providing access to earlier approved versions.
- **FR-005** — Each approved version MUST retain its steps, approval time and archived evidence references. Browser users MUST be able to open a matching sanitized example in the existing viewer. MCP results MUST include guarded references suitable for opening the same example.
- **FR-006** — Updates MUST publish atomically. Earlier approvals and their provenance MUST be immutable, and a pending update MUST leave the current approval visible.
- **FR-007** — Publishable text MUST be sanitized before review and publication. Access MUST treat text as inert content and serve only sanitized playbook text and normalized archive examples.

### Key Entities

- **Playbook** — Stable identity bound to one classified project.
- **Draft** — Pending proposed content and source references with a revision identifier for review and approval.
- **Approved version** — Immutable ordered content, evidence references and approval time.
- **Example reference** — Stable archived document identity, project and recorded snapshot identity.

## Success Criteria

- **SC-001** — In the staged and approved fixture workflows, zero pending steps or draft records are returned by ordinary retrieval or approved playbook lookup.
- **SC-002** — Both read surfaces discover the approved playbook in the matching project and return none in another project. The matching example opens in the sanitized viewer.
- **SC-003** — After two approvals, both versions are individually readable and retain 100% of their recorded example references in order. The default read selects version two.
- **SC-004** — Attempting to approve a stale draft, a cross-project example or a changed snapshot produces zero additional approved versions.

## Assumptions

- A local operator supplies the draft manually and reviews and approves it through the CLI. The existing workstation trust model applies.
- Approved discovery is a project-scoped catalog. Ordinary transcript search and synthesis continue to retrieve conversations through their existing paths.
- Each playbook has one pending draft at a time. Previously approved versions remain available for the lifetime of the local catalog and use the same project scope as the latest version.
- Each example points to a whole normalized archive session. The catalog retains its reviewed snapshot reference and reports an unavailable snapshot if the archive no longer serves it.
- Automatic extraction, step execution, publishing to remote users and a browser editing workflow are outside this phase.
