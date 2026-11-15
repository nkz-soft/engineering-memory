# Validation: Automatic Coding-Agent Session Import

Use a private, disposable operator profile with a provisioned isolated test backend and a synthetic corpus. Keep raw files under ignored data or OS temporary directories.

1. Seed a supported Codex snapshot under a date directory and a supported Claude Code snapshot under a project directory. Use a different searchable fact in each. Place a competing session outside the configured roots and a secondary transcript in an excluded directory.
2. Set the source roots using the [CLI contract](contracts/import-sessions.md). Make the two main snapshots older than the quiet period and run `engineering-memory import-sessions --json`. Expect two imports, one per source. Use the existing MCP search and conversation tools to check each fact, the original timestamp and the sanitized archive. Confirm neither competing session is present.
3. Repeat the command. Expect one unchanged entry per source and zero extractions in the recording-store test. Resume one session with material new content, wait for eligibility and rerun. Confirm the updated content retains its document ID. Verify the existing archive replay command still works with the native source removed.
4. Add a recent file, a settled malformed file and a settled valid file. Expect a defer, a failure and an import in the appropriate source summaries, and a nonzero exit for the failure. Stabilize or repair the affected files and rerun. Confirm both are eligible and previous successes remain unchanged.
5. Start a second capture while the first holds the lock. Confirm it reports busy without importing and that the next run can proceed after the first exits.
6. On Windows and Ubuntu, confirm fresh setup leaves scheduling off. Enable a user-owned Task Scheduler task or systemd user timer with the same configured one-shot command. Let it pick up a newly settled synthetic session, check the result and recall, then disable the schedule and confirm no subsequent run is made.

During implementation, run `uv run --locked pytest -q` and `uv run --locked ruff check .`. Use the existing isolated live contract setup for the backend recall check and record each platform's scheduler result.
