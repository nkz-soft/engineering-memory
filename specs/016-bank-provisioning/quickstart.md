# Validation Quickstart: Bank Provisioning

These are planned Phase 2 commands; the provisioning command and tests do not exist yet.

1. Install dependencies with `uv sync --locked --group dev`.
2. Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`.
3. Start the pinned local self-hosted service using docs/development/local-hindsight.md and configure existing environment settings. Keep credentials out of shell transcripts and fixtures.
4. Run `uv run pytest tests/integration/test_bank_provisioning.py -v` with the opt-in configuration documented during implementation. The tests must generate unique scratch banks, observe initial 404, provision, compare exact mission, repeat, replace an older mission, and preserve unrelated configuration plus seeded synthetic memories. Delete only each test's own scratch bank in cleanup. No live skips count as acceptance.
5. After the automated scratch-bank check, run `uv run engineering-memory provision` deliberately against the configured operator bank. Expect exit 0 only after exact read-back. Run it twice and expect unchanged mission and no new memories.
6. Demonstrate offline safe failures through CLI/MockTransport tests, including token canaries, mismatch and interrupted-run convergence. Do not break the operator's running service for failure injection.

Provisioning precedes the first import. Policy updates affect future extraction; this command never re-extracts old conversations. Record live prerequisites, commands and actual outcomes with the implementation; planning makes no runtime verification claim.
