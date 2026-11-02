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

## Phase 2 commands and review notes

The implemented source checks run with:

```powershell
uv run pytest tests/unit/test_claude_source.py tests/contracts/test_claude_source.py tests/integration/test_claude_cli.py tests/integration/test_claude_pipeline.py
```

To exercise the additional mixed-source recall check against an isolated live contract stack:

```powershell
$env:ENGINEERING_MEMORY_LIVE_CONTRACT = '1'
$env:ENGINEERING_MEMORY_LIVE_STORE_URL = 'http://127.0.0.1:8889'
uv run pytest tests/integration/test_claude_live.py -v
```

This creates and removes only a unique synthetic test bank. Without the opt-in flag, it skips
explicitly. It is an additional check, not automatically selected by the existing contract runner.
Recorded execution results and review findings are in [verification.md](verification.md).
