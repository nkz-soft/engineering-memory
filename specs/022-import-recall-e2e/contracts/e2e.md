# End-to-end gate contract

No production interface changes. Proposed developer entry point: `uv run python deploy/hindsight/e2e.py`.

- Starts only disposable testcontainers resources using the existing engine image digest and deterministic extraction fixture. Dynamic host ports prevent collisions.
- Runs the explicitly selected import/recall case with live mode enabled, then validates a JUnit report for the required identities with zero skips, errors or failures. Empty or absent reports fail.
- Returns zero only after successful evidence checks and cleanup. Dependency unavailability, startup failure, malformed responses and timeout fail closed.
- Positive import uses real adapters and normal provision/import commands. No fake memory path is accepted.
- Evidence must match independently specified decision, source identity, project, repository, importer version, complete tags and historical temporal grounding; archived original/normalized forms and successful state must exist.
- Provenance's import time is distinct from the original time stored in engine metadata and temporal grounding. Both historical evidence fields must match the fixture instant after timezone normalization.
- Scratch bank, network, containers and temporary paths are uniquely owned by the run; teardown occurs on every outcome. Cleanup failure cannot be presented as a clean pass.
- Bounds: readiness 600 seconds, tests 420 seconds, teardown 90 seconds, CI job 25 minutes. Ordinary offline pytest explicitly skips live-only cases; required runner treats skips as failures.
