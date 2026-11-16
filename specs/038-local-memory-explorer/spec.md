# Feature Specification: Local Memory Explorer

**Feature Branch** `038-local-memory-explorer`
**Created** 2026-11-16
**Status** Draft
**Input** [Issue #84](https://github.com/nkz-soft/engineering-memory/issues/84), step 3 of [roadmap #81](https://github.com/nkz-soft/engineering-memory/issues/81). Deep Recall prerequisite #82 is delivered by PR #92.

## User Scenarios & Testing

### User Story 1 - Explore existing project memory (P1)

An engineer opens the local explorer, selects a project scope by entering its known project slug, and searches already imported memory. Each match shows its original provenance and opens the sanitized source conversation.

**Independent test** Use an imported corpus with matching terms in two projects. Select one project and verify that only its results appear and that a result opens the matching conversation.

1. Given an imported project, when an engineer searches with its scope, then the explorer displays matches with source, original time when known and stable document identity.
2. Given a long conversation, when the engineer opens a result and advances, then the explorer shows the next page of sanitized messages and stops at the end.
3. Given a successful query with zero matches, when the result loads, then the explorer displays an empty state and keeps the selected scope and query available for retry.

### User Story 2 - Inspect evidence from a cross-session answer (P1)

An engineer asks a question about the selected project, reads Deep Recall's answer and inspects a cited passage in its archived message.

**Independent test** Ask a question with verified support in two sessions. Open a citation beyond the first conversation page and check its message, field and quote against the archive.

1. Given a completed answer, when the engineer opens a citation, then the explorer lands on the cited message and identifies the cited text or tool field.
2. Given a partial answer, when results arrive, then the explorer shows verified claims and their citations alongside the coverage limitation.
3. Given insufficient evidence, failed verification or an unavailable service, when the request returns, then the explorer communicates the corresponding state and keeps the question for retry.

### User Story 3 - Open a private local session (P2)

An operator starts the explorer on their workstation and grants a browser session access using a credential from the launcher.

**Independent test** Open two browser contexts on the same workstation. Authenticate one context and verify that the other cannot read memory.

### Edge Cases

- A stale citation or missing archived conversation shows an unavailable evidence state. An unrelated message cannot substitute for it.
- Session messages, tool fields and generated text can contain markup. Render them as inert text.
- Rapid query or scope changes keep the most recently submitted result visible, including its associated scope.
- Empty archive, backend outage and missing synthesis configuration have distinct user-visible outcomes.

## Requirements

### Functional Requirements

- **FR-001** The explorer MUST run as a local, read-only browser interface for an operator with an existing memory installation.
- **FR-002** The engineer MUST be able to enter and change the project slug and run scoped search and Deep Recall.
- **FR-003** The explorer MUST show results from the existing memory access service, using its unchanged provenance, document identities and original timestamps.
- **FR-004** The engineer MUST be able to browse the existing corpus through search results and paginated sanitized conversations.
- **FR-005** A citation MUST open its precise document and zero-based message position, identify the evidence field and preserve the verified quote. A stale or invalid anchor MUST show unavailable evidence.
- **FR-006** The explorer MUST distinguish loading, empty search, unavailable operation, partial answer, insufficient evidence and failed verification. A failed request MUST preserve the submitted scope and query.
- **FR-007** Protected reads MUST require a per-launch credential. The listener MUST be loopback-only. The explorer MUST serve sanitized content, render retrieved text inertly and avoid persisting queries or results in the browser.
- **FR-008** The explorer MUST work with existing imported conversations without re-import or data migration. Existing CLI and MCP tools retain their contracts.

### Key Entities

- **Project scope**: a known project slug mapped to the existing project tag.
- **Search match**: retrieved fact with its source, original time and stable archived document identity.
- **Deep Recall answer**: claims, verified citations, status and coverage information from the shared access service.
- **Evidence anchor**: document identity, message index, field, optional tool index and verified quote.
- **Conversation page**: sanitized messages and the next available offset.

## Success Criteria

### Measurable Outcomes

- **SC-001** In an existing two-project corpus, scoped search returns the seeded match and excludes the competing project. Opening the result displays matching provenance and supports pagination.
- **SC-002** A cited question spanning two conversations displays verified evidence, and selecting a citation after the first page lands on the exact matching message and field.
- **SC-003** The browser shows distinct outcomes for empty search, unavailable operation, partial recall, insufficient evidence and failed verification in controlled scenarios.
- **SC-004** Browser, CLI and MCP reads for the same seeded query or archive page agree on stable identities, provenance and evidence. An unauthenticated or cross-origin request exposes zero history.
- **SC-005** The launch and main user journeys are reproducible on Windows 11 and Ubuntu 24.04 using an existing configured corpus.

## Assumptions

- Version one assumes one local operator and a known project slug. Corpus browsing means scoped search and transcript navigation. A project catalog and an unfiltered archive index are outside this issue.
- The evidence panel includes the cited message and evidence field. Dedicated timeline, session viewer and diff views are tracked by #85 and #86.
- Deep Recall needs existing synthesis configuration. Search and conversation access remain available when only synthesis is unconfigured.
- A browser session covers a single launcher process. Deployment, package distribution changes and shared hosting are outside this issue.
