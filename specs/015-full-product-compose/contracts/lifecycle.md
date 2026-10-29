# Lifecycle contract

This is an orchestration contract, not a new engine or network API. Command names below describe roles; final CLI arguments must follow upstream product features.

- Development start: validate inputs, build repository image, start proxy/engine, wait within startup deadline, invoke one-shot product provisioning, then return success. Initialization failure is nonzero. Subsequent imports require initialization success.
- Provision/import/status: explicit Compose one-shot services using the product CLI. Provision is idempotent; failed mission configuration must not report readiness.
- MCP: launch a product access process with attached stdin/stdout, `-T`, no host port and no pseudo-terminal. MCP protocol alone goes to stdout; safe lifecycle diagnostics go to stderr. Consumer disconnect terminates the process and its ephemeral container.
- E2E: explicit opt-in, validate credentials/prerequisites, allocate unique ownership identity, start isolated dependencies, provision, import synthetic export, await extraction, assert retrieval through product MCP, re-import unchanged content, verify skip/no duplication, cleanup and return result. The scenario must not use direct-engine recall as retrieval.
- Skip: absent opt-in/credentials or unavailable product prerequisites is reported explicitly before creating live resources. A configured requested live run failing credentials, routing, provisioning or extraction is a failure.
- Deadline: positive finite startup, extraction, total and cleanup limits. Retry loops consume their stage budget; no unbounded subprocess or poll.
- Cleanup: accept only a validated E2E identity created by this invocation; reject development/unknown projects. Target exact project/network/volume ownership. No prune, broad directory deletion or development reset. Cleanup failure cannot erase scenario failure; if scenario passed and cleanup failed, return failure with recovery identity.
- Reset: separately documented explicit destructive development command; ordinary stop does not remove volumes.
- Report: status, safe stage/category, duration and cleanup result; never credentials, environment dumps, rendered configuration or conversation payloads.

## Offline verification cases

Test invalid/missing inputs, negative deadlines, duplicate attempted identities, two independent identities, init failure, dependency timeout, extraction failure, cancellation, cleanup timeout/failure, foreign/dev project cleanup rejection and secret sentinel suppression. Parse effective Compose with nonsecret sentinels; assert one shared engine definition, init gates, internal-only proxy/MCP, no E2E published ports or global volume/container names.
