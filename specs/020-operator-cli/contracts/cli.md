# CLI contract

## Surface

| Command | Flags | Behavior |
|---|---|---|
| `engineering-memory provision` | `--json` | Apply and verify configured shared-bank retain mission. |
| `engineering-memory import` | `--export PATH` or `--from-archive`; optional `--force`, `--json` | Import export or replay configured archive. Exactly one source selector required. PATH uses the existing export reader's supported input formats. |
| `engineering-memory status` | `--json` | Read latest durable import outcomes locally. |
| `engineering-memory --version` | none | Preserve installed-version behavior. |
| `engineering-memory --help` and each command's `--help` | none | Describe every accepted flag without constructing adapters. |

Configuration stays in existing environment settings, including configured archive/state paths. No secret flags, bank-per-project selection, dry-run, background scheduling or retrieval commands.

## Exit codes

- 0: completed successfully, including empty inputs, all skips, and status reporting remembered failures.
- 1: operational/configuration failure or any failed/terminal import result, including partial success.
- 2: usage error, including absent or conflicting import source selectors.
- 130: interrupted invocation, after resource cleanup.

Status describing failed records is a successful inspection (0); failure to inspect is 1.

## Output

Default output is readable prose with command-specific summaries. Import includes imported/skipped/failed counts, safe failed item identity/stage and terminal stage when present. Status labels its view as latest persistent state, lists records and imported/failed totals, and explains skips are per-run only. No bodies, titles, raw exceptions or credential values.

`--json` on any operational command produces exactly one JSON object on stdout followed by a newline. Diagnostics/logs go to stderr. Ordinary progress/colour/prose is forbidden on stdout. All structured results carry `schema_version: 1`, `command` (`provision`, `import`, `status`), `status` (`success`, `partial_success`, `failure`) and `error` (null or a fixed category). No dynamic exception messages.

- Provision success: common fields plus `bank` (configured identifier), `mission_verified: true`. Failure uses `mission_verified: false`.
- Import: common fields plus `imported`, `skipped`, `failed`, `terminal_error` (stage/null), `outcomes` (array). Each outcome carries source, source_id, document_id, status, completed_at, error (stage/null), state_record_failed. Times are ISO 8601 UTC. Preserve the pipeline's null identities and terminal-error distinction.
- Status: common fields plus `imported`, `failed`, `records`. Records ordered by source then source_id contain source, source_id, document_id, status, recorded_at, error (allowlisted stage or `unknown`/null). No content hashes or raw stored error text needed for this view.
- Pre-execution failure: common fields with command-specific empty data, error category (`configuration`, `input`, `archive`, `state`, `memory`, `internal`, `interrupted` or `usage`). Counts remain zero rather than implying successful work. Preserve any available import report after a terminal source failure.

Application validation errors with --json follow this envelope and code 2. Framework parser errors/help/version retain Typer behavior (e.g. unknown flag, invalid option type); this exception is documented for script authors. Interrupts emit an interrupted envelope when command output has not already been emitted.

## State boundary addition

`ImportState.iter_records() -> Iterator[ImportRecord]` yields one latest record per (source, source_id), ordered by that key. No network, mutation or skip writes. Corrupt/unavailable state uses existing typed boundary errors. SQLite validates existing schema; a missing database is treated as empty by status without calling initialize. Implementations/fakes must satisfy shared contract tests. This is current state, not a run ledger; failures without durable identity may appear only in the original run report.
