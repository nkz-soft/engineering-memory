# Guided Workstation Setup Implementation Plan

**Branch** `036-guided-workstation-setup`
**Spec** [Guided Workstation Setup](spec.md)
**Issue** [#94](https://github.com/nkz-soft/engineering-memory/issues/94)

## Summary

Add a rerunnable `engineering-memory setup` terminal wizard to the bundled workstation CLI. Windows offers it from the interactive installer. Ubuntu presents it as the next command after package installation, in the user's session. The wizard prepares the existing private profile, checks and starts the existing stack, provisions the shared bank, and guides optional MCP registration and history import.

## Technical Context

- Python 3.13, Typer, Pydantic v2, existing dotenv readers, Docker Engine 28 or newer and Compose 2.24.4 or newer.
- Windows 11 x64 and Ubuntu 24.04 LTS amd64. Use the installed standalone executable, with the existing Windows per-user installer and Ubuntu package.
- The private `app.env` and `compose.env` contract stays in effect. The active archive, SQLite state and backend volume remain durable across retries.
- Follow [the setup contract](contracts/setup.md) for prompts, outcome and error behavior. See [research](research.md) and [data model](data-model.md) for integration decisions.

## Constitution Check

| Principle | Compliance |
| --- | --- |
| I. Raw archive | Selected history enters through the existing importer and writes original and normalized records to the active local archive. |
| II. Provenance and stable identity | Reuse existing source keys, timestamps, tags, document IDs and import-state deduplication. |
| III. Test-first | Each slice starts with a failing test. Cover profile and secret handling, client and import boundaries, and installed end-to-end recall and source access. |
| IV. Replaceable boundaries | The wizard orchestrates existing configuration, deployment, provisioning and ingestion entry points. Clients register the existing read-only MCP entry point. |
| V. Secret handling | Store local credentials privately, write no values to output or MCP settings, and keep the existing sanitizer and stdio serving contract. |

The design uses the existing single bank, explicit provisioning step and stack. No constitution deviation or architecture decision record is needed. Recheck these constraints when reviewing implementation.

## File and verification map

Task-level commands belong to Phase 2. Run each focused test with `uv run --frozen pytest <test-file> -q` before and after the corresponding implementation.

| Slice | Work | First regression checks |
| --- | --- | --- |
| Profile and readiness, FR-001–004 | Add `cli/setup.py` for orchestration and `setup_profile.py` for profile loading and writes. Register the command in `cli/__init__.py`. Use `cli/stack.py` and the existing provision operation after settings are committed. | `tests/unit/test_setup_profile.py` and `tests/unit/test_workstation_setup.py` verify blank secret keeps current value, paired endpoints stay in sync, writes preserve unrelated settings, second-file write failure is recoverable, unsafe permissions block writes, and a failure before provisioning results in zero imports. |
| Client registration, FR-005–006 | Add `setup_clients.py` for user-profile and executable detection, scoped registration and safe status. Resolve the installed serve executable without depending on an updated Windows PATH. | `tests/unit/test_setup_clients.py` uses fake clients and isolated profiles to verify exact argv for paths with spaces, current-profile override, no write on decline or match, and preservation or recovery of a conflicting registration. |
| History selection, FR-007–009 | Add `setup_history.py` to discover source candidates and dispatch selected candidates via `cli/runtime.py`. Reuse current acquisition validation where a format needs its acquisition path. | `tests/unit/test_setup_history.py` covers nested agent roots, duplicate candidate paths, unsupported inputs, an unreadable candidate, opt-out, per-source failures and aggregate counts. Verify unchanged history against existing re-import coverage. |
| Installer and operating guide, FR-001 and FR-009 | Update `packaging/workstation/windows.iss`, `packaging/workstation/smoke.py` and `docs/operations/workstation-install.md`. Keep Ubuntu package maintainer scripts free of interactive setup. | Extend `tests/structure/test_workstation_release.py` to verify post-install Windows launch flags and Ubuntu packaging shape. Smoke-check the installed setup command on both build targets. Follow [clean-machine validation](quickstart.md). |

## Review Focus

- Interrupted profile writes and concurrent setup runs leave an existing profile recoverable and reject stale updates.
- A provider key with dotenv metacharacters round-trips without interpolation and stays out of diagnostics.
- Agent profiles with identical names or project-specific registrations do not receive out-of-scope edits.
- Recursive agent discovery selects eligible snapshot files and avoids directory symlinks and junctions.
- A failed or skipped candidate never blocks later selections or counts as an imported source.

## Alternatives Considered

The documented manual flow remains available for custom deployments. A wizard shared by both platforms keeps one configuration and retry contract. Separate installer-native screens would duplicate this logic, and prompting from the Ubuntu package script would run under the package manager's privilege context. A native file picker can be added later if users need one.
