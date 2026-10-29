# Feature Specification: Full-product local development and E2E environment

**Feature Branch**: `015-full-product-compose`
**Created**: 2026-10-29
**Status**: Draft, ready for planning review
**Input**: Issue #55 — Add full-product Docker Compose for local development and E2E tests.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start a repeatable development environment (Priority: P1)

A developer configures a model provider and starts the application, memory engine and model proxy without relying on previously configured containers or a manually created bank.

**Why this priority**: Real integration work is currently blocked by implicit machine setup.
**Independent Test**: From a clean checkout and documented prerequisites, start the environment and verify bounded dependency readiness and successful repeated initialization.

**Acceptance Scenarios**:
1. **Given** valid provider configuration, **When** the documented startup command runs, **Then** all dependencies become ready and explicit bank/mission initialization succeeds before import is permitted.
2. **Given** missing required configuration, **When** startup is requested, **Then** it fails before extraction with actionable diagnostics that omit secret values.
3. **Given** an initialized environment, **When** it is restarted and initialized again, **Then** archive, import state and engine records remain available without duplicate initialization effects.
4. **Given** a source edit, **When** the documented rebuild workflow is followed, **Then** the repository-built application exercises the edited code.

### User Story 2 - Prove import and retrieval through the product (Priority: P1)

A developer runs a disposable live scenario using synthetic history, the product importer and its read-only memory access surface.

**Why this priority**: Dependency health and mocked extraction cannot establish that the product works.
**Independent Test**: Run the single documented E2E command with credentials and verify real extraction, retrieval, unchanged re-import and cleanup.

**Acceptance Scenarios**:
1. **Given** implemented product prerequisites and valid credentials, **When** live E2E runs, **Then** it provisions its own bank, imports synthetic history, verifies original and sanitized archives, original time/provenance and retrieval through MCP stdio, and confirms unchanged re-import does not duplicate data or repeat extraction.
2. **Given** two concurrent runs and a running development environment, **When** either succeeds or fails, **Then** each run uses distinct state and cleanup removes only its own resources, preserving the other run and development data.
3. **Given** unavailable services, invalid model routing or failed extraction, **When** E2E runs, **Then** finite startup/extraction/completion deadlines produce a failing exit status and safe diagnostics.

### User Story 3 - Validate infrastructure without model credentials (Priority: P2)

A contributor validates configuration and lifecycle safety offline and can distinguish that result from a real product E2E result.

**Why this priority**: Pull requests must remain testable without provider secrets.
**Independent Test**: Run offline checks without credentials and inspect the live-run skip report.

**Acceptance Scenarios**:
1. **Given** no provider credentials, **When** offline validation runs, **Then** configuration and isolation checks execute and live E2E is explicitly reported as skipped, never passed.
2. **Given** an externally configured CI environment, **When** it opts into live E2E with externally injected secrets, **Then** it uses the same lifecycle and failure semantics as a local run.
3. **Given** Windows Docker Desktop or Linux, **When** an operator follows the guide, **Then** setup, stop, persistence, destructive reset and troubleshooting are documented, with unverified platform steps explicitly identified.

### Edge Cases

- Initialization failure prevents import and E2E even when dependency health passes.
- Cancellation, runner crashes and cleanup failure preserve the primary failure and identify owned resources for recovery without dumping configuration or payloads.
- Existing external proxies require a container-reachable URL, alias and explicit authentication mode; localhost inside a container is not the host.
- Empty or malformed provider configuration fails preflight; actual model authorization/routing failures fail the live readiness stage.
- Absent product prerequisites block full-product acceptance; infrastructure-only success is not a substitute.
- An unexpected or development project identifier is rejected by destructive test cleanup.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Supply a self-contained local environment containing the repository-built application, pinned self-hosted engine and configured model proxy, plus an explicit external-proxy alternative.
- **FR-002**: Development and E2E MUST share the engine service definition and settings; environment-specific overrides MUST avoid divergent engine configurations.
- **FR-003**: Required model route and credentials MUST be explicit operator inputs, with a nonsecret example explaining required/optional values. Images MUST be pinned or reproducibly built.
- **FR-004**: Initialization MUST deliberately invoke product provisioning, configure the retain mission idempotently, and gate imports/tests on successful completion after bounded dependency readiness.
- **FR-005**: Import, provisioning, status and E2E MUST be explicit one-shot operations. Consumer access MUST remain read-only MCP over stdio, without a network listener or web application.
- **FR-006**: Development MUST preserve archive, import-state and engine data across ordinary stop/restart, support source changes, and require a separately documented destructive reset.
- **FR-007**: Each E2E run MUST own a unique project, bank, archive, state database, network and volumes; any published ports MUST avoid collisions. Cleanup MUST target only run-owned resources.
- **FR-008**: Live E2E MUST use synthetic exports and product-level import/retrieval, await actual extraction completion, verify archives/time/provenance, retrieve an expected fact and its sanitized conversation through MCP, and verify unchanged re-import skips extraction without duplicates.
- **FR-009**: Startup, extraction, scenario execution and cleanup MUST have finite deadlines. Failures MUST return nonzero status and bounded safe diagnostics; cleanup MUST run on success, failure and handled cancellation.
- **FR-010**: Credentials, authorization headers, conversation payloads and rendered secret-bearing configuration MUST never enter logs or reports. Host bindings MUST default to loopback; internal services MUST not be unnecessarily published.
- **FR-011**: Offline automated checks MUST validate configuration, dependency gates, isolation, cleanup guards and failure semantics. Live tests MUST be opt-in with explicit skipped reporting when unavailable.
- **FR-012**: Document first run, configuration, external proxy, source development, persistence, stop/reset, E2E, CI secret injection, troubleshooting and Windows/Linux validation status. Preserve or redirect engine-only instructions.
- **FR-013**: Infrastructure MAY land before product prerequisites, but full-product acceptance MUST remain pending until real provision/import/MCP/re-import capabilities are available and a live run records exact commands and outcomes.

### Key Entities

- **Environment configuration**: selected mode, route alias, endpoint, credential references and finite deadlines; no committed secret values.
- **Run identity**: unique ownership token relating project, bank and disposable state; distinct from the fixed shared development bank.
- **Initialization result**: success/failure for bank and retain mission; prerequisite for ingestion.
- **Run report**: scenario status, safe failure category, elapsed waits, cleanup outcome and explicit live skip reason.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A clean checkout with documented prerequisites reaches initialized development readiness with one startup command and no manually created proxy or bank.
- **SC-002**: One live test command verifies import, fact/conversation retrieval and unchanged re-import; every invalid-dependency or extraction failure terminates within configured finite deadlines with nonzero status.
- **SC-003**: Two concurrent live runs complete or fail independently with zero shared-state collisions and zero changes to development or unrelated resources.
- **SC-004**: Ordinary development restart preserves all three data categories; only the explicit reset removes them.
- **SC-005**: Offline checks run without provider credentials; every unavailable live scenario is visibly skipped and no unexecuted live result is claimed as passing.
- **SC-006**: Every documented platform has a recorded validation result or a clearly marked outstanding validation item.

## Assumptions

- Docker Compose is installed; operators supply a working model account, route and credentials. No particular paid provider is mandated.
- A rebuild workflow is sufficient for source development; hot reload is not required.
- Development uses `engineering-global`; uniquely named disposable E2E banks are test isolation only.
- Features #16, #17, #19, #21, #23 and #24 provide adapter, provisioning, pipeline, CLI, E2E assertions and re-import behavior; #18 owns contract tests and #25 owns Hermes integration. This feature orchestrates those capabilities rather than implementing substitutes.
- At the planning baseline, main includes #15 deployment but not the working importer/provisioner/MCP surface. Pending prerequisites must remain visible.
- Phase 1 local orchestration fits ARCHITECTURE.md sections 21–22. No new source, production platform, network MCP, worker architecture or governance amendment is proposed.
- Ambiguity review found no question requiring a human decision; the assumptions above settle source development, provider choice and incremental delivery.
