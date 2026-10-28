# Data Model: Local Hindsight Development Setup

There is no new application database schema. These are deployment and verification values; raw archive and import state are unchanged.

## Deployment profile

| Field | Meaning and constraints |
|---|---|
| image | Official full 1.1.0 image with immutable digest recorded in plan |
| api bind | Host loopback only; default port 8888, configurable positive valid host port |
| persistence | Dedicated Compose named volume; survives normal down/restart |
| shared memory | 1 GiB for upstream embedded database |
| proxy base URL | Required container-reachable compatible API URL, no embedded credentials |
| proxy alias | Required nonempty operator-owned model route; no application backend default |
| proxy key | Externally supplied secret when proxy authenticates; a documented nonsecret placeholder only if an unauthenticated proxy's client requires it |
| embedding/reranking | Explicit local providers |
| worker identity | Stable within this development Compose project |

A profile transitions unconfigured → configured → starting → ready → stopped. Failures are explicit and do not imply successful extraction. Image/model download is a separately documented preparation phase.

## Application connection

Use existing ENGINEERING_MEMORY_HINDSIGHT__BASE_URL and optional TOKEN. Existing required ENGINEERING_MEMORY_LLM__BASE_URL/key remain application configuration; they are not implicitly forwarded into Hindsight. Host-side and container-side proxy addresses may differ. New application settings are unnecessary.

## SmokeRun

| Field | Validation and lifecycle |
|---|---|
| run_id | Fresh UUID generated per invocation |
| bank_id | engineering-memory-smoke- plus run_id; no caller bank override |
| document_id | Generated deterministically from run_id and fixed probe purpose |
| content | Fixed synthetic fact containing a distinctive expected answer; no input text/file |
| timestamp | Fixed fixture instant, explicitly synthetic |
| deadline | Positive finite duration; default 180 seconds total |
| stage | readiness, retain, completion if queued, recall, cleanup |
| outcome | passed only after expected recalled fact; otherwise failed with safe stage/status |
| keep_scratch | Explicit boolean; default false; true supports restart inspection |

Within-run document identity is reused if observing completion; no automatic retain-retry policy is added. Cleanup checks exact generated bank identity before any deletion. Cleanup failure is visible even if write/recall succeeded; the output must distinguish it from the primary failure.

## RoutingEvidence

Run start/end UTC times and bank ID correlate with proxy metadata (request identity, time, configured alias, success status). No proxy key, authorization header or payload is recorded. Zero observed proxy requests means routing acceptance is incomplete. Multiple LLM calls may occur; do not require exactly one call.

## Operational boundary

Scratch state is derived synthetic test data, not archived history. Normal shutdown preserves storage. An explicit reset targets only the named development volume and is documented separately. Neither cleanup nor reset may target application archive/import-state paths or arbitrary banks/volumes.
