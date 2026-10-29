# Research: full-product orchestration

## R1 — Reuse the existing engine

Decision: Preserve the engine-only entry point and share one canonical service definition with product overlays.
Rationale: `deploy/hindsight/compose.yaml` already pins Hindsight 1.1.0 by digest, local embeddings/reranking, safe logging, 1gb shared memory, embedded database volume and bounded readiness. `tests/structure/test_hindsight_deployment.py` expects exactly one service in that entry point. Its fixed project name and loopback port are development defaults, not appropriate E2E identities.
Alternatives: Duplicating the service risks drift; silently replacing the entry point breaks existing operators/tests.

## R2 — Separate readiness from product success

Decision: Health gates dependency startup; successful product provisioning gates import; actual extraction completion and MCP retrieval gate E2E success.
Rationale: Existing `/health/ready` and synthetic direct-engine smoke cannot establish working product import or proxy model authorization.
Alternatives: Mock-only or health-only success fails issue acceptance.

## R3 — Cross-platform owned lifecycle

Decision: Python runner uses argument-array subprocess invocation, unique project/bank identity, no E2E published ports and finite stage/outer deadlines. Cleanup uses the validated owned project; never global prune.
Rationale: Existing Python runtime works across Windows/Linux and can test failure semantics offline. Project-scoped volumes isolate archive, SQLite and engine storage.
Alternatives: Per-platform shell scripts multiply cleanup/error behavior; fixed ports and global volume names prevent concurrency.

## R4 — Application and E2E packaging

Decision: Start with documented image rebuild for source edits; introduce a dedicated test image target or controlled fixture/test mounts for E2E.
Rationale: Dockerfile installs noneditable code and runs as UID 10001; mounting src alone does not change that package. `.dockerignore` excludes tests/data. Runtime must not gain pytest solely for deployment tests; first-use persistent directories must be writable.
Alternatives: Implicit source mounts give misleading development results; running all services as root weakens the existing image policy.

## R5 — Explicit provider route and immutable proxy

Decision: Internal LiteLLM has a named alias backed by operator-selected model/environment credentials; external-proxy mode supplies container-reachable URL/alias/auth explicitly. Select and verify an actual LiteLLM image digest during implementation before use.
Rationale: The issue does not prescribe a model provider and extraction requires real credentials. No unverified image pin is invented in planning.
Alternatives: An implicit host proxy recreates the original failure; a provider credential in a tracked config violates Principle V.

## R6 — Prerequisites and staged evidence

Decision: Infrastructure may land independently; full-product acceptance remains blocked on #16/#17/#19/#21/#23/#24. #18 owns adapter contract tests and #25 owns Hermes integration.
Rationale: At origin/main e65afa2, CLI is an empty Typer shell, access only a package scaffold and engine smoke directly calls Hindsight. Existing local deployment guide records deferred live/platform validation. No current product E2E pass can be claimed.
Alternatives: Implementing placeholder CLI/MCP behavior here would duplicate upstream work and obscure boundary ownership.

All design unknowns are resolved at planning level. Concrete image availability and upstream executable command spellings are implementation validation items, not unresolved user scope choices. Findings are based on checked-out repository source, not assumptions about current upstream releases.
