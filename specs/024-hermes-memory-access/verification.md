# Verification record: Hermes memory access

Date: 2026-11-02. Python 3.13.15; official MCP SDK 2.3.0. Only synthesized history
was used in tests. No private corpus or local credentials were published.

## Test-first evidence

- `python -m pytest tests/unit/test_access.py -q`: failed collection because
  access.service did not exist; implementation then passed all 25 initial cases.
- `python -m pytest tests/unit/test_access_cli.py tests/integration/test_access_mcp.py -q`:
  failed because load_access_settings did not exist. The independent subprocess run
  failed with `No such command 'serve'` before the command was implemented.
- Missing-required-argument privacy regression failed with PRIVATE_SENTINEL echoed
  by the SDK high-level validation. Low-level SDK callbacks fixed it; regression passed.
- Raw-string regression confirms query `null` remains a string; tags `null`, explicit
  null tags and extra arguments are rejected before reaching recall.

## Executed checks

- `uv sync --locked`: succeeded before SDK addition; `uv add mcp` synchronized and
  locked the official SDK. No stack choice displaced (ADR-008).
- Targeted access, structural and live-runner tests: 64 passed before the final
  competing-project unit case; access/protocol rerun including that case: 29 passed.
- `python deploy/hindsight/e2e.py`: 32 passed in 21.52 seconds, exit 0. Isolated
  testcontainers deployment, synthetic extraction, live backend, real subprocess
  MCP client. Gate requires test_import_to_access_tools, so skipping the consumer
  protocol case cannot produce a passing live gate. Resources were cleaned up.
- `uv run ruff check .`: all checks passed.
- `uv run pytest -q`: 1962 passed, 35 skipped in 93.42 seconds. Opt-in live tests
  are skipped in the ordinary run and separately exercised by the Docker gate.
- `uv run ruff format --check .`: 444 files already formatted.
- `git diff --check`: passed. A final added competing-project unit case passed in
  the targeted access/protocol run (29 passed); final metadata/guard run: 58 passed.

The first full regression found two expected structural guard updates (filled access
module and authorized MCP dependency); both guards were deliberately updated.

## Independent review

The requesting-code-review skill dispatched a fresh-context reviewer. It found
(1) SDK missing-argument errors echoing inputs and (2) SDK JSON preprocessing changing
string inputs, including potentially widening invalid tag filters to an unscoped query.
Both were fixed using official low-level Server callbacks, which preserve raw values
and pass them through strict service validation. Reviewer rechecked the changes and
reported no remaining actionable implementation finding. Regressions cover both.

## Outstanding live consumer acceptance

No `hermes` command was found on the Windows PATH or in the Ubuntu WSL environment;
no local Hermes configuration was found in the checked standard locations. No tested
Hermes version or fresh Hermes conversation can therefore be reported. The committed
configuration follows the official Hermes command/args MCP recipe, but actual Hermes
acceptance and a second clean Hermes setup remain UNVERIFIED.

The PR must remain a draft until the operator procedure in
[hermes-memory.md](../../docs/operations/hermes-memory.md) is completed with synthetic
public evidence. SDK/live-backend results prove the server path, not model tool use
inside Hermes. Task T013 remains unchecked; no Phase 1 completion claim is made.
