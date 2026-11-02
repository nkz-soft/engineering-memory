# Quickstart validation: Claude chat source

This guide describes verification after Phase 2 implementation; these commands are not evidence
that the source already exists. Use Python 3.13/uv and synthetic exports only.

1. Run `uv sync --locked`, then `uv run pytest tests/contracts tests/unit tests/integration`.
   Require the Claude source contract to run all CS cases without skips and parser/integration
   tests to prove order/time/identity, failure isolation, no leaked secrets and original replay.
2. Put a synthetic supported export at `data/claude/conversations.json`; keep data ignored.
   Run `uv run engineering-memory import --source claude-chat --export data/claude/conversations.json --dry-run --json`.
   Expect projected import/skip decisions with zero archive/state writes and memory calls.
3. Provision the configured local bank through `uv run engineering-memory provision`, then run
   `uv run engineering-memory import --source claude-chat --export data/claude/conversations.json --json`.
   Verify originals and sanitized normalized forms, claude-chat ids/tags and source timestamps.
4. Repeat step 3: unchanged records are skipped, without extraction. Run
   `uv run engineering-memory import --source claude-chat --from-archive --force --json`
   after removing the input export: originals reconstruct the same normalized conversations.
5. With the existing local Hindsight live-test configuration, import a distinct ChatGPT synthetic
   fact too. Query through the existing memory access surface unfiltered and with source:claude-chat;
   verify both sources unfiltered, only Claude when filtered, and sanitized get_conversation output.
   Record the exact opt-in live pytest invocation and results once those tests are implemented.
6. Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`.
   Preserve actual command output for review. No live service or extraction was run in planning.
