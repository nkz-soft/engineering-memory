# Quickstart validation (after implementation)

Use only synthetic fixtures. From the feature worktree:

```powershell
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/contracts/test_codex_source.py
uv run pytest
uv run engineering-memory --help
uv run engineering-memory import --help
```

Follow the existing CLI import syntax with `--source codex` and a staged synthetic JSONL file. Confirm the implemented help before selecting positional paths or configuration options. First dry-run; then import against an explicitly provisioned local test bank. No real history is required.

Expected: original bytes and sanitized normalized conversation archived; codex:{native-id} identity and source:codex provenance. Repeat unchanged input and observe no extraction; modify a tool output and observe an update to that identity. Delete staged source and replay the original archive to prove independence. Use a valid/invalid/valid fixture batch and expect two imported sessions and one safe failure.

Live acceptance requires configured local Hindsight and the existing access surface. Recall a unique synthetic fact with source:codex plus its known project; verify the result and absence from a different-source filter. The implementation must add the exact opt-in test command here. Missing live configuration means UNVERIFIED, not PASS.

Planning verification only: review links, FR/SC coverage and constitution gates; no implementation tests are claimed in Phase 1.
