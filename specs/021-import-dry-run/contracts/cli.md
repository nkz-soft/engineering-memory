# CLI contract: Dry-run extension

`engineering-memory import (--export PATH | --from-archive) --dry-run [--force] [--json]`

Exactly one source selector remains required. Dry run uses the same source formats and rules,
never constructs a memory client, never checks bank provisioning and never writes archive/state.
Missing state means empty; existing state opens read-only and is validated. Existing settings
validation still applies. Ordinary import/provision/status contracts remain feature 020's.

## Output

Text begins with an explicit dry-run marker and would-import/would-skip/failed totals. Each
successful row prints document_id, canonical project tag, original timestamp, unique sorted
redaction categories (empty means none) and would_import/would_skip. Failed rows show available
identity and fixed stage, with unavailable metadata clearly absent. No text bodies or titles.

JSON emits exactly one object plus newline on stdout; logs go to stderr. Fields:

- schema_version: 1; command: import; dry_run: true.
- status: success / partial_success / failure; error: null or existing fixed CLI error category.
- would_import, would_skip, failed: integer counts; terminal_error: fixed Stage/null.
- outcomes: ordered preview rows with source, source_id, document_id, project, timestamp,
  redaction_categories, decision and error as defined in ../data-model.md.

Actual imported/skipped counters are not part of preview output. Early application errors use
the preview envelope with empty outcomes and zero counts. Framework parsing retains Typer behavior.
Exit codes: 0 for complete preview (including empty/all skips), 1 for any failed or terminal
result/configuration error, 2 for application usage errors, 130 for interruption.

## Guarantees and limits

Preview actions match a subsequent successful real run when corpus, rules/configuration and
initial state are unchanged, including force and repeated identities. Preview does not forecast
remote retain, archive-write or state-write failures. Preparation failures on predicted skips
are preview failures even though ordinary import can skip without preparing metadata.
