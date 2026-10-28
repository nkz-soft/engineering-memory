# Feature Specification: Local Hindsight Deployment

**Feature Branch**: `014-local-hindsight-deployment`

**Created**: 2026-10-27

**Status**: Draft — ready for planning review

**Input**: [Issue #15](https://github.com/nkz-soft/engineering-memory/issues/15), "Document a local Hindsight deployment routed through the LiteLLM proxy". Provide a reproducible development instance, required environment, proxy extraction routing and a scratch-bank write/read smoke check, with extraction visible in the proxy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start a reproducible local instance (Priority: P1)

As a developer on a clean supported machine, I can follow the guide to start and reach my own memory engine without knowing another developer's setup.

**Why this priority**: Later Phase 1 work cannot validate a real engine until this exists.

**Independent Test**: Follow the documented prerequisites and start commands on a machine without an existing Hindsight deployment; wait for readiness and restart without losing its test data.

**Acceptance Scenarios**:

1. **Given** documented prerequisites and an existing reachable proxy, **When** the start procedure runs, **Then** a version-pinned local instance becomes reachable within a bounded wait.
2. **Given** missing required configuration or an unavailable service, **When** setup runs, **Then** it fails with actionable diagnostics rather than appearing ready.
3. **Given** a working deployment, **When** it is stopped and restarted normally, **Then** its persistent test data remains and the guide explains storage ownership.
4. **Given** default deployment settings, **When** host listeners are inspected, **Then** published engine access is limited to loopback and no database port is exposed.

---

### User Story 2 - Prove extraction uses the configured proxy (Priority: P1)

As a developer, I can prove that extraction travels through the existing proxy and change its underlying model without editing application code.

**Why this priority**: Reachability alone proves neither extraction nor the required routing.

**Independent Test**: Retain a synthetic fact and correlate the run with successful proxy metadata for the configured alias, without logging bodies or credentials.

**Acceptance Scenarios**:

1. **Given** the proxy URL, key when required and a valid configured alias, **When** the smoke write runs, **Then** extraction is observed in that proxy.
2. **Given** a different backend behind the same proxy alias, **When** the deployment is used again, **Then** no application source change is needed.
3. **Given** a rejected key, missing alias or unreachable proxy, **When** the write runs, **Then** the smoke check exits unsuccessfully with a safe explanation.
4. **Given** successful write/read results but no proxy observation, **When** acceptance is reported, **Then** routing remains unverified rather than being inferred from configuration.

---

### User Story 3 - Validate tests against an isolated scratch bank (Priority: P2)

As a developer, I can run a smoke command that writes a synthetic fact and recalls it, then use the same instance for future engine contract tests.

**Why this priority**: It turns a setup guide into a repeatable verification path and unblocks #16.

**Independent Test**: Run the smoke command twice; each run uses a unique scratch bank, finds its own fact and leaves the production bank untouched.

**Acceptance Scenarios**:

1. **Given** a ready local instance, **When** smoke runs, **Then** it writes synthetic content to a new scratch bank and verifies that the expected fact is recalled.
2. **Given** an accepted but incomplete write, **When** readiness or extraction does not complete within the overall deadline, **Then** smoke fails rather than reporting acceptance as successful retention.
3. **Given** production data exists, **When** smoke runs or cleans up, **Then** no production-bank write, configuration change or deletion occurs.
4. **Given** the setup guide, **When** a test author follows its connection instructions, **Then** the engine URL and optional token match the existing settings boundary, and offline tests need no live instance.

### Edge Cases

- A host URL works on the host but not in a Linux container; the guide distinguishes host and container addressing, including loopback-only proxies.
- Port conflicts, slow first image/model preparation, insufficient resources and unsupported Docker configurations produce identifiable setup failures.
- Credentials containing punctuation must be passed without printing them or interpolating them into command-line arguments.
- Health succeeds but extraction or recall fails; these are separate verification stages.
- Empty/malformed recall results, failed operations, unexpected HTTP status and deadline expiry fail the smoke check safely.
- Interrupted runs leave only their uniquely named scratch data; cleanup is bounded to that run's bank.
- Normal shutdown preserves storage; destructive volume removal is a separate explicit documented action.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Provide a complete start/readiness/stop/restart guide and a version-pinned scripted local development deployment.
- **FR-002**: Document supported operating systems, runtime prerequisites, resource needs, network assumptions and persistent storage.
- **FR-003**: Require extraction through the configured existing OpenAI-compatible proxy endpoint, with credentials supplied externally and no hardcoded underlying model.
- **FR-004**: Document the proxy alias contract and how operators change the actual model in proxy configuration.
- **FR-005**: Default exposed engine endpoints MUST bind only to host loopback; database storage and ports MUST remain private.
- **FR-006**: Provide a bounded smoke command that writes a synthetic fact, verifies it through recall and reports nonzero on any unsuccessful stage.
- **FR-007**: Smoke MUST generate a new scratch bank per run and MUST NOT accept arbitrary conversation input or target the production bank.
- **FR-008**: Record successful proxy observation as a separate acceptance requirement, using metadata only; HTTP health or engine success alone does not prove routing.
- **FR-009**: Diagnostics MUST omit credentials, authorization headers, full endpoint credentials, request/response bodies and private conversation content.
- **FR-010**: Document how host-run tests connect using existing application settings without bypassing the settings boundary.
- **FR-011**: Keep ordinary automated tests offline; live validation MUST be explicitly invoked and use synthetic data only.
- **FR-012**: Preserve engine state across normal restart and distinguish normal shutdown from destructive reset.
- **FR-013**: Keep engine-specific protocol code within the existing memory/hindsight implementation area and leave production bank provisioning, retain mission and importer implementation to their own issues.
- **FR-014**: Default embeddings and reranking MUST run locally; no additional external content-processing route may be introduced silently.

### Key Entities *(include if feature involves data)*

- **Deployment profile**: Pinned engine version, local endpoint, persistent storage and externally supplied extraction route.
- **Proxy route**: Container-reachable URL, optional credential and alias whose backend is owned by the proxy operator.
- **Smoke run**: Unique scratch bank, synthetic fact/document identity, start/end time, deadline and write/recall outcome.
- **Routing evidence**: Operator-confirmed successful proxy request metadata correlated to the isolated run, excluding payloads and credentials.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A clean supported machine reaches a ready local instance by following only the committed guide and documented prerequisites.
- **SC-002**: Smoke exits zero only after retaining and recalling its expected fact; wrong content, unavailable engine and extraction failure each yield nonzero.
- **SC-003**: Two consecutive runs use distinct scratch banks and do not mutate engineering-global.
- **SC-004**: At least one successful extraction is observed in the configured proxy during a documented isolated smoke window; missing evidence is explicitly incomplete acceptance.
- **SC-005**: Normal stop/restart retains test data, and inspection confirms only loopback engine publishing with no host database port.
- **SC-006**: Automated failure tests show missing configuration, bad authentication, malformed recall and timeout fail without exposing supplied secret canaries.
- **SC-007**: The offline test suite passes without Docker, proxy access, credentials or a live engine.

## Assumptions

- Issue #15 is Phase 1 infrastructure with no prerequisites and unblocks #16. Governance selects none; it changes no bank strategy or engine contract.
- The operator already has a LiteLLM proxy and an alias supporting the engine's structured extraction requests. Creating or administering that proxy is outside scope.
- Default support is Docker Compose v2 with Linux containers on Linux and Docker Desktop on Windows/macOS. No Kubernetes or hosted engine deployment is introduced.
- This is development-only: loopback access with unauthenticated local engine API is the default. Existing optional engine bearer-token settings remain available for separately secured instances.
- The smoke payload is a purpose-built synthetic infrastructure probe, not an import of history. It grants no general direct-write path to consumers and does not alter the raw archive or production ingestion guarantees.
- A unique generated scratch bank is an allowed test override of the single production-bank strategy. Any cleanup is restricted to that generated bank.
- The actual model stays in proxy configuration; the engine necessarily receives an externally supplied proxy alias, which is not added as an application model setting.
- Model/image downloads require initial network access; local embeddings/reranking do not imply an offline installation.
- Live deployment acceptance will require the operator's actual proxy environment. This planning run does not launch services, spend extraction calls or claim live validation.
- Clarification review found no blocking ambiguity. Concrete timeouts, safe diagnostics, routing evidence and platform choices are resolved in the design.
