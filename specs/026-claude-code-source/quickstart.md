# Quickstart validation (after implementation)

Use only synthetic fixtures. Prerequisites: Python 3.13, uv, configured local archive/state and,
for live recall, the existing provisioned self-hosted Hindsight bank and model configuration.

1. Run `uv run pytest tests/unit tests/contracts tests/integration` and verify parser, resumable
   source, metadata precedence, sanitizer, archive replay and CLI registration scenarios pass.
2. Generate a synthetic JSONL snapshot using the new test fixture helper: one failed command with
   a distinctive fabricated error, investigation, an Edit diff and successful retry. Set cwd to
   `/work/orchard`, mention a conflicting project in prose, and plant a synthetic secret in output.
3. Run `uv run engineering-memory import --source claude-code --export PATH --dry-run`.
   Expect one planned session and no retention/state writes.
4. Run `uv run engineering-memory import --source claude-code --export PATH` twice.
   Expect one import followed by one unchanged skip with zero extra extraction calls.
5. Change an output in the snapshot and import again. Expect an update under the same document id.
6. Move the snapshot away and run `uv run engineering-memory import --source claude-code --from-archive --force`.
   Expect successful replay from archived originals with original session identity and project.
7. Through the existing memory access test client, recall the fabricated root cause filtered to
   `source:claude-code` and `project:orchard`, then open the returned document. Expect the failed
   command, error, investigation and fix in order, correct tool association and no planted secret.
   Repeat against live Hindsight; a fake-store pass alone cannot satisfy the root-cause recall gate.
8. Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`. Record command outputs
   and separately report live recall outcome, including a configuration-based skip if unavailable.

PATH denotes the synthetic snapshot created in step 2, not a private production session.
