# Research: Local Hindsight Deployment

Research checked official upstream sources on 2026-10-27. These are documentation/registry observations, not a claim that a live instance was exercised. A read-only research agent checked deployment/provider/API details as required by speckit-plan.

## R1 — Reproducible engine identity

**Decision**: Plan the full standalone 1.1.0 image, pinned by tag and digest. Verify that identity/platform manifest when implementing.

**Rationale**: The [official v1.1.0 release](https://github.com/vectorize-io/hindsight/releases/tag/v1.1.0) was published on 2026-10-21. The [official container registry](https://github.com/vectorize-io/hindsight/pkgs/container/hindsight) lists full-image tag 1.1.0 with digest sha256:50311d02b4d5d2b7c5242bd336edf8735df8374eaad496a92f49c83b37d2aa06. An immutable pin is this project's reproducibility choice; availability and live behavior still require validation.

**Alternatives considered**: latest floats; an undocumented existing instance is not reproducible; building upstream from source adds unnecessary setup.

## R2 — Full local container and storage

**Decision**: One Compose service with embedded database, dedicated named volume, loopback API publishing, local embedding/reranking and no published UI by default.

**Rationale**: [Official installation documentation](https://hindsight.vectorize.io/developer/installation) describes standalone API/UI ports 8888/9999, volume /home/hindsight/.pg0 and 1 GiB shared memory. Full images provide local models; slim requires external providers. Named volume ownership avoids bind-mount UID friction. Our loopback mapping, dedicated volume and omitted UI are project-specific safety/simplicity decisions. The initial image/model preparation requires network access; the guide must state actual resource prerequisites and observed startup costs rather than promise an offline or instant installation.

**Alternatives considered**: external database/embedding/reranking services expand prerequisites; Kubernetes is outside development scope.

## R3 — OpenAI-compatible proxy route

**Decision**: Use provider=openai with externally supplied LLM_BASE_URL, LLM_API_KEY and LLM_MODEL alias. No physical backend model is specified in application code or Settings.

**Rationale**: The [official models guide](https://hindsight.vectorize.io/developer/models) distinguishes compatible HTTP endpoints from LiteLLM SDK dispatch. The proxy owns the alias-to-model mapping. This design sends extraction through the existing proxy without introducing SDK routing. Keyless proxies may still require a nonsecret client placeholder for the pinned OpenAI provider; confirm this at implementation and document it, rather than silently substituting a provider credential.

**Alternatives considered**: the LLM provider named litellm is SDK dispatch; direct upstream credentials or fallback routes would defeat the intended proxy routing.

## R4 — Configuration ownership and local processing

**Decision**: Compose supplies HINDSIGHT_API_* values to the container; the smoke module consumes the existing engineering-memory Settings. Keep keys for proxy and engine distinct. Set EMBEDDINGS_PROVIDER and RERANKER_PROVIDER to local.

**Rationale**: [Upstream configuration](https://hindsight.vectorize.io/developer/configuration) separates engine LLM, embeddings and reranking settings. Engine authentication is optional, using tenant extensions when enabled. Application Settings already owns host connection URL/token and proxy URL/key; loading those fields does not reconfigure another process. Default local loopback deployment needs no engine auth extension. No new model setting is added to the application.

**Alternatives considered**: overload one token for both endpoints, expand Settings with container deployment fields, or assume one proxy flag controls every model operation.

## R5 — Smoke protocol and current contract discrepancy

**Decision**: Implement engine-specific HTTP smoke within memory/hindsight, preferring synchronous retain and a bounded recall verification. Verify the pinned /openapi.json before finalizing route assumptions.

**Rationale**: The [retain guide](https://hindsight.vectorize.io/developer/api/retain) and [HTTP reference](https://hindsight.vectorize.io/api-reference) currently describe POST /v1/default/banks/{bank_id}/memories; the [recall guide](https://hindsight.vectorize.io/developer/api/recall) describes /memories/recall. Architecture §9 records /retain and /recall instead. This mismatch is evidence for #16's running-contract verification, not permission to rewrite the production contract during infrastructure setup. Smoke uses the pinned server's verified operational routes. Require a response with the expected synthetic fact, not merely a 2xx write.

If a write is queued, the [operations guide](https://hindsight.vectorize.io/developer/api/operations) distinguishes successful completion from pending/processing/failed/cancelled states. Our deadline and safe failure behavior are local design decisions. Do not assert async completion semantics from HTTP acceptance alone.

**Alternatives considered**: a health-only smoke proves no extraction; echoing arbitrary recalled text proves no expected fact; blindly trusting moving docs risks version mismatch.

## R6 — Proxy proof and privacy

**Decision**: Live acceptance includes metadata-only proxy observation in an isolated smoke window, separately from smoke HTTP success. Report request ID/time/status/alias where available; never demand body logging.

**Rationale**: This is an inference from the issue's acceptance criterion: engine success cannot establish which route handled extraction. A dedicated alias/key identity and isolated run allow useful correlation without publishing content or credentials. Exact proxy observability depends on the operator's existing deployment and must be documented during implementation.

**Alternatives considered**: infer routing from environment alone; enable request/response debug logs; commit operator proxy configuration or tokens.

## R7 — Bounded scope

**Decision**: Synthetic-only scratch banks and direct administrative probe; no arbitrary history input, production bank provisioning, importer or consumer integration.

**Rationale**: Architecture Phase 1 item 1 and issue #15 establish infrastructure before #16. Existing Settings allows scratch-bank test overrides; ADR-008 continues to govern consumers. The smoke is not an importer and claims no provenance/retain-mission contract validation.

**Alternatives considered**: use engineering-global, add a consumer write tool, or bundle #16's contract tests/mission configuration here.

## Resolved assumptions and remaining validation

No clarification questions remain. Docker resources, network/proxy credentials, alias and live proxy observation are explicit execution prerequisites, not missing product decisions. No deployment was started during planning. The immutable image, exact server routes, provider keyless behavior and live smoke/proxy acceptance must be checked during Phase 2; no mocked test can stand in for those live results.
