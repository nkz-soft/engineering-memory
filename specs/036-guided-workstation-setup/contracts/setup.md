# Installed Setup Contract

## Entry point

```text
engineering-memory setup
```

Use a terminal in the current user's session. Outside an interactive terminal the command exits with a message before modifying profiles or starting Docker. The Windows interactive installer offers an optional launch. Ubuntu users run the command after apt completes.

## Prompts and changes

1. Show current or default nonsecret profile values. Echo no credential input. Blank accepts an existing secret when present. Ask for a provider/model and credential when required and offer the optional custom provider endpoint. Validate editable values and confirm before persisting. Default ports are 8888 and 4000. Use the existing per-user data locations when paths are omitted.
2. Check Docker, offer backend startup and wait for readiness. Provision the shared bank before allowing import. Report a bounded, stage-specific recovery message for failures.
3. Show detected Codex and Claude Code targets. Apply only selected user registrations. Match the absolute installed executable and sole argument `serve`. A conflict requires explicit replacement confirmation. A failed replacement leaves or restores the prior entry and reports the result.
4. Show eligible agent histories and local exports by type and path. Accept an explicit local path and source type when needed. Import only the confirmed selection using existing operators. Print per-source imported, skipped and failed counts and any safe source-level failure. Skipping the entire import is a normal outcome.

End with a concise summary of completed, deferred and failed steps. On a hard setup failure or requested action failure, return nonzero after showing the summary. A person can retry by running the same command. Suppress raw subprocess output that could contain secrets or history.
