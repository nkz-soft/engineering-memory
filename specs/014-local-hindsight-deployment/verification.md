# Verification: Local Hindsight Deployment

## Scope and operator deferral

The second `/issue-to-pr 15` invocation resumed the committed plan on branch 014-local-hindsight-deployment. All 16 requirement-checklist entries were complete; no extension hooks exist. The operator subsequently explicitly deferred live Hindsight/LiteLLM validation. Implementation, documentation, offline tests and a draft PR remain in scope; live startup/extraction/restart/proxy acceptance is intentionally pending.

Docker Desktop was initially stopped; it was started before that deferral. Before the deferral, a registry metadata query confirmed the planned image digest (no image was downloaded by that query). A queued image pull was rejected by automatic approval review after the deferral because it conflicted with the revised scope. It was not retried or bypassed. No Hindsight deployment or extraction call was performed.

## Pinned upstream inspection

Read-only GitHub inspection of tag v1.1.0 confirmed the registry digest and source/API routes in hindsight-api-slim/hindsight_api/api/http.py and hindsight-clients/go/api/openapi.yaml. Retain uses /memories, recall /memories/recall, health /health/ready and bank DELETE /v1/default/banks/{bank_id}. RetainResponse exposes success, bank_id, items_count, async and optional operation identity. Source inspection is not live server validation. Architecture section 9's route discrepancy remains documented for #16; no production contract was silently changed.

## Test-first evidence

- Dependency guard: tests/structure/test_packaging.py first failed because httpx was absent, then passed after uv add httpx updated pyproject.toml/uv.lock.
- Deployment tests: all four first failed because the Compose profile did not exist. After implementation, effective rendered loopback ports/volume/provider alias and required-input errors passed. These Docker Compose config operations do not start containers or need a daemon.
- Smoke tests: 37 initial tests failed due to the missing module before implementation; the implemented in-memory transport suite then exercised completed/queued operations, HTTP and malformed-data failures, deadlines, generated-bank isolation, cleanup and credential safety.
- Token regression: invalid non-ASCII and CRLF tokens reproduced unsafe encoding/header behavior; validation now fails safely before transport.
- Stale-fact regression: a fixed fact from an older run initially passed a new run. Smoke now retains and verifies a codename containing a fresh per-run suffix.
- Shutdown review regression: delayed transport close exceeded the total deadline and raw RequestError exposed a synthetic canary. Explicit bounded shutdown now reports fixed safe diagnostics, preserves primary errors and generated run metadata. Both tests pass.
- Initial full suite found the existing skeleton behavior guard needed this feature to explicitly register memory.hindsight. The allowlist and rationale were updated without exempting its parent/siblings; the guard's negative tests still pass.

## Independent review

A read-only code-review agent identified unbounded/unsanitized client shutdown. The finding was reproduced and fixed, and the reviewer confirmed no remaining blockers. The reviewer ran 12 offline static/configuration/help checks; async execution was unavailable in its sandbox and no result was claimed for those tests. The main execution environment ran the async MockTransport checks normally. A nonblocking named-project consistency suggestion was covered by an assertion and corrected.

## Offline coverage

Generated scratch banks only; deterministic document identity within each run; fixed synthetic timestamp; per-run expected fact; no arbitrary history or production-bank option; engine/proxy credential separation; no redirect/environment proxy use; safe URL/token validation; OpenAPI methods before writes; completed retain/queued operation handling; recall mismatch/invalid response; single retain request; monotonic overall and per-request budgets; scoped cleanup and safe bounded shutdown; independent proxy-observation status. Compose checks verify the actual rendered configuration without a daemon or real credentials.

## Results

Intermediate full suite after module registration: 1619 passed, 4 existing skips in 47.98s. Final results are recorded below after the final reviewed code run.

## Live acceptance — deferred

Image pull/platform runtime, actual readiness, real retain/recall, restart persistence and successful LiteLLM-side observation were not run at the operator's request. No offline test substitutes for those outcomes. The draft PR must retain this limitation and issue #15 must not be represented as live-validated. Guide commands are reproducible future instructions, not claimed executed results.

## Final offline verification

- `uv run pytest tests/unit/test_hindsight_smoke.py tests/structure/test_hindsight_deployment.py -q --tb=short`: **49 passed in 2.84s**.
- `uv run pytest -q --tb=short -rs`: **1621 passed, 4 skipped in 46.50s**.
- `uv run ruff check .`: **All checks passed!**
- `uv run ruff format --check .`: **302 files already formatted**.
- `uv lock --check`: **Resolved 33 packages**, exit 0.
- `git diff --check`: exit 0; staged check repeated before commit.

The four skips are existing fake-store unsupported failure hooks (two) and Windows symlink-permission tests (two). No offline failure is being hidden by the live-validation deferral. All code-review blockers are resolved. Task T012 remains explicitly deferred, not completed or replaced by mocks.

## Delivery

Implementation commit: dbda10b. Draft PR: https://github.com/nkz-soft/engineering-memory/pull/54. Issue #15 moved to in-review. T001–T011 and T013 are complete; T012 remains deferred at the operator's request. The isolated worktree is retained, and no merge or live startup was performed.

## CI follow-up: ANSI-formatted CLI help

The Linux job at https://github.com/nkz-soft/engineering-memory/actions/runs/40506851291/job/122198284775 failed because help-test assertions searched raw ANSI output for an uninterrupted option name. The CLI exited successfully. Reproduced the exact assertion failure locally using Typer's original theme/highlighter with Rich ANSI rendering forced: one colored case failed and the plain case passed. The test now normalizes text with Text.from_ansi and exercises both render modes, explicitly checking that the colored case really contains escapes. Runtime behavior and live-validation deferral are unchanged.

`uv run pytest tests/unit/test_hindsight_smoke.py -q --tb=short`: 46 passed in 1.42s. Ruff lint/format and git diff --check passed. Full-suite results follow below.

Full offline rerun: `uv run pytest -q --tb=short -rs` — **1622 passed, 4 skipped in 45.15s**. No live Hindsight/LiteLLM operations were executed.
