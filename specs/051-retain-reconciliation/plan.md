# Implementation Plan: Retain reconciliation

**Spec**: [spec.md](spec.md)

The store currently retains the operation identifier in memory. A poll timeout
bubbles up as a generic exception and the pipeline records a terminal retain
failure. A new process lacks the identifier and can submit the same content again.

Use an optional tracked retain capability alongside the synchronous store
interface. The adapter supplies an opaque destination-scoped receipt. The
pipeline persists it after archiving and before sending, records acceptance,
then waits within the existing deadline. Transient submission retries within
the initial run reuse the same receipt and payload. A resumed run reconciles
matching inputs by receipt using status queries. Manual and automatic runs also
check unmatched receipts for the selected source. An acquired ZIP's completion
depends on its own inputs. SQLite adds a receipt table with
an additive migration. Terminal reconciliation writes the outcome and import
health in the transaction that clears the receipt. Manual and automatic
commands share the profile writer lock.

If delivery cannot be observed, keep the receipt uncertain because no status
response can prove the write never happened. Do not infer success from recall or
the existence of a document. A historical failed record without a receipt
cannot be linked reliably to a particular backend submission.

## Constitution check

- I. Both archive forms precede tracked submission and remain available for replay.
- II. The same document identity, raw content hash and provenance are used. A
  saved receipt prevents duplicate extraction after restart.
- III. Synthetic CLI and backend regression tests start red. Verify isolated
  Hindsight operation and recall behavior against the pinned release.
- IV. The adapter owns backend endpoints and status interpretation. Existing
  synchronous memory and import-state protocols stay available.
- V. The send path still receives sanitized data. Receipts contain no content
  or credentials. Status output omits receipt tokens.

## Verification

Run the synthetic regressions with `uv run pytest tests/integration/test_retain_reconciliation.py`.
For the slow-backend scenario, start `deploy/hindsight/compose.contract.yaml` as a
fresh Compose project. Set `ENGINEERING_MEMORY_LIVE_CONTRACT=1` and direct
`ENGINEERING_MEMORY_LIVE_STORE_URL` and `CONTRACT_FIXTURE_URL` to the project's
loopback ports. Run that test module and `tests/integration/test_live_hindsight_contract.py`
against the isolated project. The test holds extraction across a shortened CLI
deadline, starts a second CLI process, compares backend operations and checks
both MCP tools. Remove the test project's containers and volume afterward.
