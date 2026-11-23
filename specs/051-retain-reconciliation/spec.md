# Feature Specification: Retain reconciliation

**Branch**: `051-retain-reconciliation`

**Issue**: #124

## User stories

1. An operator imports a synthetic session whose retain is accepted but takes longer than the CLI wait. The CLI and local state report pending work. A later invocation observes the outcome without another retain submission.
2. A lost or malformed submission response leaves an uncertain outcome. A later invocation checks the same receipt. A definitive submission rejection or terminal extraction failure is reported as failed.
3. Manual import and automatic session import use the same rules, including after process exit and when the original file is gone. Archive replay preserves exact source bytes and unchanged successful imports are skipped.

## Requirements

- Persist a scoped receipt before sending the request and distinguish confirmed acceptance from unconfirmed delivery.
- Reconcile through read-only status queries. Unavailable or missing status preserves the receipt. A terminal status commits the result and clears the receipt atomically.
- A changed input can be submitted after the older content reaches a terminal status. An unrelated receipt does not block a ChatGPT export from completing.
- Preserve deterministic document identity, original timestamps, provenance, sanitization and existing read and write interfaces.
- Keep previous import records readable. Legacy failures without a receipt do not establish whether a submission was accepted.
- Verify with invented data and an isolated slow backend. Never run against a user bank.
