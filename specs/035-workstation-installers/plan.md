# Workstation Installers Implementation Plan

> Execute through Spec Kit after the issue-to-PR review gate, with red → green
> verification for each task.

**Branch**: `035-workstation-installers` | **Date**: 2026-11-14 | **Spec**: [spec.md](spec.md)

## Summary

Bundle the installed Python 3.13 CLI as a PyInstaller one-directory payload.
Ship it as an Inno Setup per-user EXE for Windows 11 x64 and a DEB for Ubuntu
24.04 LTS amd64. Bundle backend Compose assets that reuse the canonical
Hindsight service and existing LiteLLM model routing. Run the existing CLI and
stdio MCP server on the host and reach services via loopback.

## Technical Context

Use uv's locked application dependencies, native x64 build jobs, PyInstaller
with package metadata and runtime resources, and platform package tools.
Docker Desktop with Linux containers on Windows or Docker Engine on Ubuntu
runs Hindsight and LiteLLM. Document Compose v2.24.4 or later as the initial
floor, and verify the exact recipe against that floor. Archive and SQLite paths
are absolute, host-local, and writable by the operator. Hindsight persists in a
named Docker volume. The checksummed binary release targets `v0.1.0`.

## Constitution Check

| Principle | Design and check |
| --- | --- |
| I. Raw archive | Use the existing importer and local archive. Test original and sanitized archive persistence after reinstall and unchanged import skip. |
| II. Provenance and identity | Preserve the existing import and Hindsight contracts. Assert the retrieved source has the fixture's stable document ID and original timestamp before and after reinstall. |
| III. Test-first | Add failing packaging, path, lifecycle and release checks before implementation. Keep existing contract and live import/recall suites. |
| IV. Boundaries | Use existing CLI settings and adapters. Keep Compose orchestration at the operator boundary. Codex and Claude Code invoke the existing read-only `serve` command. |
| V. Secrets | Inject provider credentials via private configuration into the required process environments. Keep Docker bindings on loopback, suppress secret-bearing subprocess output and keep MCP stdout for protocol messages. Verify diagnostics and release artifacts contain no test credential. |

The design stays within ARCHITECTURE.md §§21–22. Docker remains the deployment
mechanism for Hindsight and LiteLLM. The workstation packaging extends the
constitution's current Docker-only packaging entry. Include an ADR and a
versioned constitution update in the implementation PR to record the native
CLI artifact choice. Review both with the PR before merging.

## Project Structure and Work Sequence

1. **Installed CLI and private configuration** (`packaging/workstation/`,
   `src/engineering_memory/settings.py`, `tests/unit/test_workstation_settings.py`).
   Test that an installed CLI reports the version and opens config and state
   from an unrelated working directory with spaces. Test normal, offline
   status and access-only settings paths, absent or malformed config, existing
   editable settings behavior and protocol-clean startup. Bundle distribution
   metadata, package data and dynamic imports. Pass the installed profile
   through the existing settings loaders. Resolve defaults in the profile,
   without changing the calling directory or relaxing the settings schema.
2. **Backend setup and lifecycle** (`deploy/workstation/`,
   `src/engineering_memory/cli/`, `tests/unit/test_workstation_lifecycle.py`,
   `tests/structure/test_workstation_deployment.py`). Begin with tests for
   missing Docker, unavailable daemon, old Compose, occupied port, explicit
   working directory and stopping without volume removal. Add
   `stack check|start|stop|status` at the CLI operator boundary. Package assets
   with the canonical Hindsight service and existing LiteLLM routing. Invoke
   Compose with explicit paths and a stable project name. Get readiness from
   Compose health and keep plain `status` for offline import state. Document
   the manual initial configuration and explicit `provision`.
3. **Package and verify both platforms** (`packaging/workstation/windows.iss`,
   `packaging/workstation/build-deb.sh`, `tests/structure/test_workstation_packaging.py`).
   Write artifact tests first for architecture, file ownership, version, command
   discovery and absence of configuration or mutable storage from install
   manifests. Build the packages, install from the download and execute each
   clean-machine check in [quickstart.md](quickstart.md). Test running from a
   different directory and reinstalling with the backend stopped.
4. **Release automation and handoff** (`.github/workflows/release.yml`,
   `tests/structure/test_release_workflow.py`, `docs/operations/workstation-install.md`).
   Write failing checks for tag/version mismatch, partial artifact matrices and
   publishing permissions. Build both targets with pinned tooling from the exact
   tag, verify the packaged CLI version and run installation smoke checks. Carry
   the exact candidate bytes into a draft GitHub Release for full acceptance.
   Publish the draft with the two binaries and checksum sidecars only after
   both live acceptance records pass. Refetch and digest-check the public
   downloads. Tag an approved merged commit containing the release workflow.

## Review Focus

- Paths with spaces and Unicode, including a different MCP working directory.
- Repeated setup, missing or malformed config, and Windows credential-file ACLs.
- Stopped Docker daemon, startup failure and host port collision.
- Reinstall survival of configuration, named volume, raw archive and SQLite state.
- Tag mismatch, failed matrix leg, credential leakage and stale checksums.

## Verification

Run `uv run --locked ruff check .`, `uv run --locked ruff format --check .`
and `uv run --locked pytest`, then the existing live Hindsight contract
and import/recall jobs. Record results from a clean Windows 11 x64 system
and Ubuntu 24.04 LTS amd64 system using the candidate installers. The
implementation PR can carry candidate evidence and the release handoff. The
issue's public-download acceptance is only satisfied after tag publication
and checksum verification.
