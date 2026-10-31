# Research: Hindsight retry policy

## R1 — Boundary and identity

**Decision**: Retry raw requests inside HindsightStore before safe error translation and decoding.
**Rationale**: At base commit 825b015, retain creates the UUID/body once before _request and shares a monotonic deadline through polling. Keep pending identities on uncertainty. Read-only agent research independently confirmed this boundary and its test implications.
**Alternatives considered**: Whole-retain retries restart too much work; domain-error retries lose classification.

## R2 — Library and bounded timing

**Decision**: Tenacity with explicit predicate, four attempts and wait_exponential_jitter(initial=1, max=8, jitter=1), plus stop decisions using the original deadline and prospective sleep.
**Rationale**: Implements the fixed stack and exponential backoff with jitter. Attempt caps alone cannot bound repeated polling; per-request elapsed-time stops cannot replace the caller deadline.
**Alternatives considered**: Fixed delay, unbounded defaults and full-operation retries.
**Source**: [Tenacity API](https://tenacity.readthedocs.io/en/latest/api.html). Numeric defaults are project assumptions for review.

## R3 — Classification

**Decision**: Retry allowlisted HTTP statuses, HTTPX timeouts and causal connection resets only; no automatic retry for other transport failures.
**Rationale**: HTTPX distinguishes timeouts, network and protocol failures. Inspect causal ConnectionResetError/ECONNRESET without message matching. Broad TransportError, ConnectError or ReadError predicates exceed section 18.
**Alternatives considered**: All 5xx, all network failures or all unavailable errors.
**Sources**: [HTTPX exceptions](https://www.python-httpx.org/exceptions/), [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/).

## R4 — Scope, tests and observability

**Decision**: Runtime retain/poll/recall only; no provisioning/probe changes. Allowlist events and inject deterministic timing seams.
**Rationale**: provision.py is an independent async administration flow; smoke.py includes diagnostic extraction and cleanup. Existing uncertain-retry/rejected-replay tests must exhaust automatic retries before exercising later caller calls. Both injected sync and owned async transports require coverage.
**Alternatives considered**: A universal retry transport broadens scope; default exception logging risks private diagnostics.

All research items resolved; no extension hooks are installed.
