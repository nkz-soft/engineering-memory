# CLI Contract: import-sessions

## Invocation

`engineering-memory import-sessions [--json]` performs one scan and exits. It uses the same operator profile and bank as `engineering-memory import`.

| Setting | Meaning |
| --- | --- |
| `ENGINEERING_MEMORY_SESSION_IMPORT__CODEX_ROOT` | Optional local Codex sessions directory. Accept main-snapshot JSONL files at its top level and under the standard year/month/day layout. |
| `ENGINEERING_MEMORY_SESSION_IMPORT__CLAUDE_CODE_ROOT` | Optional local Claude Code projects directory. Accept main-snapshot JSONL files at its top level and directly inside project directories. |
| `ENGINEERING_MEMORY_SESSION_IMPORT__QUIET_SECONDS` | Positive quiet period for file eligibility. Default 300 seconds. |

The command requires at least one root. Other roots and client profiles are out of scope for the run. Windows junctions, symlinks and nested auxiliary transcripts are excluded from discovery. Schedule enablement is a user-managed OS setting. The scheduler action uses this one-shot command under the operator profile with an explicit executable path and access to the normal settings.

## Result

Text and JSON both identify the configured source kinds and their `imported`, `unchanged`, `deferred` and `failed` counts. Each source may also carry a fixed diagnostic category for a source-level error. JSON uses the existing CLI result envelope with a per-source collection.

A successful, empty or deferred-only scan exits zero. Missing configuration, an overlapping capture run, a source-level error or any failed candidate exits nonzero. A partial failure preserves successful import outcomes. File names, paths, content and credential values are omitted. Unchanged skips reuse the import pipeline definition.
