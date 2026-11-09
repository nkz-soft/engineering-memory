# Acquisition contract

## Boundary

`ExportSource.discover() -> Iterable[ExportCandidate]` yields local candidates ready for a check. Manual discovery yields its explicitly selected file. Watcher discovery yields stable ZIPs from the configured inbox in first-observed order. A no-candidate result is normal. Unreadable configuration or discovery is an error. Both implementations use the same archive validator and coordinator. A manual run can start immediately because the operator declares its input complete, but it still stages and validates it.

The coordinator's archive adapter stages a snapshot, publishes it by digest only after preflight, and reopens it on retry. It validates the digest of existing archived bytes before dispatch. Missing or mismatched pending blobs fail visibly and must never lead to an import from unverified bytes.

The preflight accepts stored or DEFLATE-compressed single or contiguous zero-based split archives, including empty arrays. Limits are 4 GiB compressed, 16 GiB expanded, 100,000 members, 64 MiB of directory metadata and 32 Mi characters per JSON record. It rejects truncated, encrypted, unsupported or structurally ambiguous ZIPs and incomplete arrays without invoking ingestion. It checks limits against actual bytes read as well as advertised metadata. It never extracts paths from the archive. Validation failures are scoped to the new candidate. Report a safe category and stop the invocation.

## CLI

- `engineering-memory acquire-chatgpt` checks the inbox configured in `ENGINEERING_MEMORY_CHATGPT_EXPORT_INBOX` and resumes pending work. The scheduler provides the cadence. A missing inbox is a configuration error for watcher mode.
- `engineering-memory acquire-chatgpt --file PATH` submits a local ZIP through the same preflight and ledger. If there is pending work, resume it before processing a fresh ZIP. Existing `import` and `--from-archive` remain available for legacy inputs and recovery.
- `--json` emits safe acquisition and import counts and an outcome. Success, duplicate, busy and empty outcomes exit 0. Acquisition failure or unsuccessful import exits 1. Interruption follows the existing CLI convention.
- `engineering-memory status --json` adds nullable `last_chatgpt_export`. When present it contains `produced_at`, `production_evidence` and `ingested_at`. Dates use UTC ISO 8601. Text status shows the same facts. A v1 store or an empty ledger yields null. A pending attempt never replaces the most recently completed entry. This status field reflects acquisition-managed imports.
- Neither structured results nor logs expose local source paths, ZIP member names, raw bytes or credentials. Operators can correlate an accepted archive by digest.
