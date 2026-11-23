# Implementation Plan: Windows Installer Maintenance

**Branch**: `049-windows-installer-maintenance`
**Date**: 2026-11-23
**Spec**: [spec.md](spec.md)
**Input**: [Issue #120](https://github.com/nkz-soft/engineering-memory/issues/120)

## Summary

Add a read-only maintenance decision ahead of the Windows installer file phase. Compare the release version and a content identity. Reuse the built-in wizard and installed helper for identical-build configuration, and retain the normal payload and guided setup sequence for accepted installs, updates and repairs.

## Technical Context

| Area | Plan |
| --- | --- |
| Runtime and packaging | Existing Inno Setup 6.5.4 Pascal Script, Python 3.13, uv and PyInstaller on Windows 11 x64. No new runtime dependency. |
| Installation evidence | Existing Inno current-user uninstall entry and a small versioned integrity manifest in the application directory. The manifest contains only build metadata and hashes of immutable payload files. |
| Mutable state | Existing user profile, provider credentials, archive, SQLite, Docker volume and client config stay under their existing owners and paths. |
| Verification | Test-first classification and verification fixtures, compiled Inno smoke matrix on a clean Windows CI runner, Windows 11 desktop acceptance with verified artifacts and a synthetic history import. |
| Constraints | Classify offline before file copy or running the installed helper. No elevation or network probe is required to detect a current-user installation. |

## Constitution Check

| Principle | Design check |
| --- | --- |
| I. Raw Archive Is the Source of Truth | Operate on application files. Archive originals and normalized history stay in their current storage. |
| II. Provenance and Stable Identity | Build identity is local installer metadata. Existing history IDs and provenance remain intact and are independently compared after updating. |
| III. Test-First | Observe failing regressions before behavior changes. Verify classification and preservation against compiled installers and keep the existing workstation test suite. |
| IV. Replaceable Boundaries | Keep decisions in packaging and reuse the existing setup helper, MCP consent, and memory access surface. |
| V. Secrets Never Reach the Memory Engine | Integrity checks read immutable installation files only. Preserve the helper's existing private request and output handling. The validation import uses synthetic data and installer diagnostics expose only safe statuses and versions. |

Pre-research and post-design checks pass. No stack, boundary or governance deviation is proposed.

## Project Structure

| Path | Responsibility |
| --- | --- |
| `packaging/workstation/build.py` | Emit or invoke generation of the Windows payload manifest within the existing release build. |
| `packaging/workstation/windows.iss` | Read and verify evidence, choose mode, protect payload work and reuse wizard pages. |
| `src/engineering_memory/cli/setup.py` and existing setup helpers | Reuse protected read, save, scan and targeted apply actions. Extend only if deferring confirmation requires it. |
| `.github/workflows/release.yml`, `tests/structure/test_workstation_release.py` and packaging smoke fixtures | Compile deterministic fixture packages and exercise real installer decisions and artifacts. Retain Ubuntu coverage. |
| `tests/unit/test_workstation_setup.py` | Cover the shared configuration/MCP behavior affected by the no-copy path. |
| `docs/operations/workstation-install.md` | Explain choices, silent outcomes, diagnostics and recovery. |

The design artifacts are [research.md](research.md), [data-model.md](data-model.md), [the installer contract](contracts/maintenance.md) and [quickstart.md](quickstart.md).

## Implementation and Verification Sequence

1. **Produce and validate evidence (FR-001–002, FR-007).** Generate a canonical sorted inventory of Windows payload paths and their SHA-256 hashes. Bind the inventory, release version and installer recipe to a SHA-256 build identity, and provide the incoming identity at compile time. Verify the installed inventory and identity before classifying a healthy installation. Exclude the manifest and installer-generated files from the payload inventory. Reject unsafe or ambiguous inventory paths before reading file content. Compare supported numeric release versions using Inno's packed numeric comparison. Exercise same-version builds, identical input, lexical versus numeric versions, missing files, modified files and invalid metadata.
2. **Select a mode before installation (FR-001, FR-004, FR-006).** Read current-user registration in the applicable registry view and resolve the same effective app root that will be used for installation. Use one production decision table for interactive and silent paths. Recheck evidence before entering the write phase or invoking an installed helper. Confirm update, replacement or repair as appropriate and preserve the version guard even when payload integrity fails. Use normal Inno exit handling and fixed log statuses for automation. Exercise both silent switches and custom or ambiguous path evidence.
3. **Reuse the wizard without payload effects (FR-003, FR-005).** Route the same settings and MCP pages before installation work in configuration-only mode. Stage edits and choices in memory until final confirmation and discard them on cancel. Retain validation, stale-edit guard, explicit registration replacement and unrelated profile preservation. Skip the payload, uninstaller and uninstall registration, PATH mutation, restart-manager actions, and startup for identical runs. Maintain the existing regular-user restriction for helper execution. A compiled test must verify that disabled install entries still leave the filesystem and registration untouched under the pinned Inno version.
4. **Preserve and verify accepted updates (FR-004–005, FR-007–008).** Use in-place installation for immutable files. Gate helper use on verification of the installed payload and identity after copying. Surface file-in-use or incomplete-install errors and let retries reclassify actual evidence. Keep mutable paths out of copy and cleanup. Compile a realistic smoke matrix, document silent and recovery behavior, and complete the Windows desktop and synthetic recall procedure in [quickstart.md](quickstart.md).

## Alternatives Considered

- **Use version or Git revision as the sole identity.** Version conflates review builds. Revision misses differences in actual packaged bytes. Use the payload inventory and installer recipe as identity inputs.
- **Always overlay the payload then open setup.** Keeps one existing code path but writes binaries and metadata on a configuration-only run.
- **Hand maintenance to the standalone setup command.** Useful as the current regular-user fallback when helpers are unavailable, but it bypasses the built-in settings and MCP wizard requested by the issue.
- **Enable unattended repair or same-version replacement.** Would overwrite files without proof of ordering or consent. Reserve both for the explicit interactive paths.
