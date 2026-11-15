# Implementation Plan: Automatic Coding-Agent Session Import

**Branch** `037-automatic-session-import` | **Date** 2026-11-15 | **Spec** [spec.md](spec.md)

## Summary

Expose `engineering-memory import-sessions` as a bounded scan of explicitly configured native histories. The command stages stable snapshots one at a time, passes them through the existing coding-agent adapters and ingestion pipeline, and returns per-source outcomes. Operators can run it directly or schedule it under their own account using Windows Task Scheduler or an Ubuntu systemd user timer.

## Technical Context

- **Runtime and CLI** Python 3.13 with uv, Typer and Pydantic settings.
- **Persistence** Existing local raw archive, SQLite import state and provisioned shared memory bank. The stable copy is held in memory only.
- **Platforms** Windows 11 x64 and Ubuntu 24.04 LTS amd64, matching the workstation packages.
- **Performance** Read one candidate at a time, skip recent files before copying, and use the existing hash skip before extraction.
- **Testing** pytest with synthetic histories, a recording memory store for extraction counts, and an opt-in isolated live backend for recall.

## Constitution Check

| Principle | Design and verification |
| --- | --- |
| I. Raw archive | The existing pipeline stores original snapshot bytes and sanitized normalized data before retention. Verify replay after the native file and temporary copy are gone. |
| II. Stable identity | Existing adapters provide the native ID and time. Use the shared import state and hash skip. Verify zero repeat extraction and an update under the same ID. |
| III. Test-first | Observe failing tests for discovery, capture races, source isolation and CLI behavior before each implementation. Include an import-to-recall regression and real engine checks where the architecture depends on backend behavior. |
| IV. Replaceable boundaries | Snapshot acquisition produces input for existing source interfaces. Reuse the pipeline via CLI runtime composition, and validate reads through the existing read-only access surface. |
| V. Secrets | Keep capture scratch space private. Route conversation content through existing sanitization before retention. Emit counts and fixed diagnostic categories without raw history, paths or credentials. |

The design fits Phase 2 in Architecture §22. Invoking an ordinary one-shot command through an operator-owned OS schedule uses the current CLI model and requires no background service under §21 or governance amendment. The checks still hold after the capture, CLI and scheduling design below.

## Project Structure

- `src/engineering_memory/ingestion/` owns bounded discovery and snapshot staging. The existing `codex/` and `claude_code/` adapters continue to parse revisions and identify sessions.
- `src/engineering_memory/cli/` and `settings.py` own configuration, pipeline composition, overlap handling and result emission.
- `tests/unit/`, `tests/contracts/` and `tests/integration/` cover capture, the command contract and shared memory behavior.
- `docs/operations/` documents setup, retry and user-owned scheduling.

## Implementation Sequence

1. Define optional capture settings and a shared discovery policy for native main-session trees. Test supported layouts, bounded traversal, link and junction rejection, inaccessible directories and deterministic ordering.
2. Implement one-at-a-time capture. Test quiet-period deferral, changes during copying, disappearance, replacement, read failures and cleanup. Recheck the path against link and junction redirection before reading and after copying. Use exact staged bytes for parsing and for the archive. Keep per-file failures resumable in the capture source and preserve adapter duplicate detection for the whole source pass.
3. Wire one pipeline pass per configured source through the current CLI runtime. Preserve aggregate outcomes on partial failure. Add a nonblocking lock for competing capture commands using one import-state path. Test busy handling, cleanup and recovery on process exit.
4. Add CLI and scheduler guidance. Validate both source kinds, unchanged retry, updated identity, coexistence of eligible and unusable files, archive replay and sanitized recall. Record isolated live and workstation scheduling checks separately.

See [research](research.md), [data model](data-model.md), [CLI contract](contracts/import-sessions.md) and [validation guide](quickstart.md) for the design decisions and expected behavior.
