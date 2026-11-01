# Quickstart validation: Import dry run

These checks apply after implementation approval; dry-run is not implemented at this planning gate.
Use synthetic export fixtures only. Configure isolated archive/state paths and install with
`uv sync --locked`. No running Hindsight or bank provisioning is required.

1. Run `uv run engineering-memory import --help` and verify --dry-run is documented.
2. Run `uv run engineering-memory import --export SYNTHETIC_EXPORT --dry-run` and repeat with
   `--json`; inspect the fields in contracts/cli.md, including metadata for predicted skips.
3. Repeat using `--from-archive --dry-run` against synthetic archived originals and `--force`.
4. In automated tests, poison memory construction/calls, archive.store and state.record;
   assert zero calls, unchanged durable bytes and no missing-path creation.
5. Compare a mixed corpus preview with a successful real run from identical initial state;
   cover new/changed/unchanged, repeated identities and force.
6. Cover empty input, corrupt/missing state, isolated bad conversations, terminal reader errors,
   metadata preparation failures, interrupts and resource cleanup. Check safe exit codes.
7. Capture stdout/stderr/logs and assert synthetic secret canaries never appear.
8. Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`.

Actual real-run parity tests use local test adapters; they incur no remote extraction costs.
