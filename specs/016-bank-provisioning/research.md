# Research: Bank Provisioning

## R1 — Reuse the pinned adapter environment

**Decision**: Target Hindsight 1.1.0 at digest `sha256:50311d02b4d5d2b7c5242bd336edf8735df8374eaad496a92f49c83b37d2aa06`, already used by #16.
**Rationale**: deploy/hindsight/service.yaml and specs/015-hindsight-memory-store/verification.md establish the deployment and successful extraction/recall checks. They do not establish bank configuration behavior.
**Alternatives considered**: Introduce another engine version or treat successful recall as proof of provisioning. Both would obscure the actual contract.

## R2 — Explicit configuration write and verification

**Decision**: Inspect the pinned OpenAPI, then use the config write described by Architecture §9 and ADR-003; prefer direct PATCH creation if the pin supports it. Use a separate dedicated creation endpoint only if the pinned contract requires it. Never use retention to create the bank.
**Rationale**: The issue explicitly requires successful provisioning after a 404, without fake memory items. GET config and PATCH config paths are engine-specific details. Upstream inspection suggests an `updates` envelope and `retain_mission` field; verify these in the pinned schema and live scratch-bank checks before implementation.
**Alternatives considered**: Bare-field guessed payload, overwriting the complete configuration, or relying on moving documentation. None proves the deployed contract.
**Evidence**: Architecture §§9,12 and ADR-003; existing store integration tests do not cover config. Exact field, request envelope, creation semantics and read-back shape are implementation validation prerequisites, not unresolved product decisions.

## R3 — Canonical mission and evolution

**Decision**: Package the complete §12 text as a resource; assert byte-for-byte equality with the fenced architecture text, defining a single terminal newline consistently. The operator reruns the command after a version-controlled policy change.
**Rationale**: Prevent wording drift and ensure both priority sections survive transport. Existing extracted memories are not rewritten.
**Alternatives considered**: CLI free-text mission option or import-time override. Neither is needed for #17 and the latter contradicts ADR-003.

## R4 — Administrative boundary and operational safety

**Decision**: Keep the operation in memory/hindsight and reuse existing settings/security conventions. Verify the final state on every invocation; report errors without bodies or credentials. Prefer convergence by rerun over deleting a partially configured bank.
**Rationale**: The read-only consumer boundary and ingestion pipeline must not gain engine administration semantics.
**Alternatives considered**: Extend MemoryStore, auto-provision on retain, or destructive rollback.

## R5 — Evidence required before completion

**Decision**: Add isolated MockTransport/CLI tests and opt-in live tests for initial 404, exact mission, repeat, changed mission and preservation. Existing deployment documentation reserves a provision role; document the CLI it can invoke, without expanding this feature into full-product initialization.
**Rationale**: Constitution requires running-instance validation for engine assumptions. Live provisioning evidence is absent today; mocks cannot satisfy it.
**Alternatives considered**: Claim live acceptance from #16's unrelated extraction checks.

## Implementation evidence (2026-10-30)

Inspected upstream v1.1.0 `hindsight-api-slim/hindsight_api/api/http.py` through GitHub: config PATCH consumes BankConfigUpdate.updates, GET returns config/overrides, and writes require HINDSIGHT_API_ENABLE_BANK_CONFIG_API. Source: https://github.com/vectorize-io/hindsight/blob/v1.1.0/hindsight-api-slim/hindsight_api/api/http.py . This confirms wire shape, not running-instance semantics.

CLI composition is the explicit exception anticipated by the plan: only cli -> hindsight.provision imports provision/ProvisionError. The architectural import guard now permits that exact edge while continuing to reject CLI store imports and ingestion/access administration imports.
