# Verification: Issue #23

## Scope and implementation

The required gate runs three live cases: normal provision/import/status CLI execution, a real-pipeline case supplying known repository and optional user context, and a real import whose wire timestamp is deliberately removed. The latter must fail the same temporal assertion used by the positive path. The CLI does not currently accept repository/user arguments, so the additional pipeline case covers those populated fields without changing the CLI or memory protocol.

All fixtures are synthetic. Testcontainers uses the canonical pinned engine image and existing synthetic extraction server, an isolated network, dynamic ports and ephemeral engine storage. The parent bounds startup/tests; a separately bounded cleanup subprocess removes only resources bearing the exact random run label, attempts remaining removals after individual failures, and fails the gate if cleanup fails.

## Test-first evidence

- `uv run pytest tests/unit/test_e2e_runner.py -q` initially failed collection because the new e2e module did not yet exist.
- `uv run pytest tests/structure/test_ci_workflow.py -q -k end_to_end` failed: no `live-e2e` job.
- The first live run passed all 18 evidence cases but exposed a cleanup error: DockerClient is not a context manager. The gate correctly returned failure.
- Added cleanup regression controls before the repair: `uv run pytest tests/unit/test_e2e_runner.py -q -k cleanup` reported 2 failed, 1 passed (missing total-deadline cleanup and missing best-effort cleanup).
- Expanded live coverage after review. The CLI case initially failed because it correctly emits the three required tags, whereas the manually assembled pipeline also supplies optional `user:synthetic`. Expectations now distinguish those supported inputs; the pipeline case still requires all four tags.
- `uv run pytest tests/unit/test_e2e_runner.py -q`: 13 passed after fixes, including report integrity, timeout propagation, readiness timeout, cleanup deadline and cleanup failure controls.

## Review

Independent review requested through the repository's requesting-code-review skill. Addressed all three findings: real CLI positive path, mismatching values for every tag namespace, and overall cleanup deadline plus attempts after individual removal errors. No production module or public interface changed.

## Final checks

- `uv run ruff check .`: all checks passed.
- `uv run ruff format --check .`: 421 files already formatted.
- `uv run python deploy/hindsight/contract.py`: 9 passed; Compose containers, volume and network removed.
- `uv run python deploy/hindsight/e2e.py`: two successive clean runs passed 19 cases each (6.22s and 6.56s pytest execution). After the final supervisor fix, a further fresh run passed all 19 (6.47s), with successful cleanup.
- `uv run pytest tests/unit/test_e2e_runner.py -q`: 16 passed, including the three added startup-supervisor regression tests (observed failing before implementation).
- `uv run pytest -q`: 1916 passed, 31 skipped in 90.41s (expected opt-in live skips).
- `git diff --check`: clean.
- Docker query for `engineering-memory.e2e-run` containers returned none after the final run.

Follow-up review confirmed no material remaining findings after the startup supervisor repair. CI itself will execute on the PR; local live gates passed without external model credentials.


- `uv sync --locked`: resolved/checked 41 packages successfully.
- Docker query for tagged end-to-end networks also returned none.

