# Windows Installer Configuration Page Implementation Plan

**Branch**: `047-windows-setup-ui` | **Date**: 2026-11-21 | **Spec**: [spec.md](spec.md)

**Goal**: Configure the installed Windows workstation in Inno Setup and let the operator explicitly opt in to backend startup and shared-bank provisioning.

**Architecture**: The wizard owns the form and consent. The installed executable shares profile parsing, validation and transactions with terminal setup. A separate operation checks and starts the stack and provisions the bank after consent.

**Tech Stack**: Windows 11 x64, per-user Inno Setup 6.5.4, PyInstaller onedir, Python 3.13, Typer, Docker Compose, existing Hindsight and pinned LiteLLM.

## Base and release dependency

At planning, updated `origin/main` was `13bc1368e6dfb240fd3e366899013dd39a099e75`, including [#107 via PR #108](https://github.com/nkz-soft/engineering-memory/pull/108). [PR #106](https://github.com/nkz-soft/engineering-memory/pull/106) for [#105](https://github.com/nkz-soft/engineering-memory/issues/105) was open. No dedicated issue for the embedded page was found. PR #106 touches the CLI setup and stack, release workflow, workstation documentation, and setup tests. Before implementation, refresh main and PR #106, rebase this planning branch if main advanced, and reconcile these touchpoints when #106 lands. Keep the Windows UI branch independent of #106 and #107 and coordinate if #106 needs to ship first. Scope is workstation setup within ARCHITECTURE.md §22, with no §21 expansion.

## Constitution Check

Initial and post-design checks find no deviations.

| Principle | Design application |
| --- | --- |
| I. Raw archive | Reuse the archive and SQLite settings. No data relocation, writes or import from the embedded page. |
| II. Provenance and stable identity | No changes to ingestion, document IDs, timestamps or deduplication. |
| III. Test-first | Observe a failing regression for each behavior change, then run the Windows package and acceptance matrix. |
| IV. Replaceable boundaries | Changes stay in installation, profile and CLI orchestration. Existing memory and ingestion boundaries and the read-only MCP surface remain intact. |
| V. Secrets | Scope key transport to the profile save and reuse protected storage. Pass no provider credentials to Hindsight, logs, answer files or process arguments. |

## Implementation sequence after approval

### 1. Share profile reads and updates

- [ ] In `tests/unit/test_setup_profile.py`, add failing tests for fresh defaults, existing and legacy profiles, redacted reads, partial profiles, invalid port and path pairs, untouched proxy fields, and rollback/locking. Cover saved credential interpolation and rotation on a provider change.
- [ ] In `src/engineering_memory/setup_profile.py`, introduce the editable values in [data-model.md](data-model.md) and a common validation/persistence path. Expose redacted read and explicit apply operations to the installer entry point. Keep the CLI's existing prompt order, save confirmation, proxy editing and cancellation behavior. Re-read the latest profile inside the existing lock at apply time, with a stale-edit check on exposed fields and no rewrite of hidden proxy or unchanged secret assignments. A read must not create a fresh profile.
- [ ] Run `uv run pytest tests/unit/test_setup_profile.py tests/unit/test_workstation_settings.py tests/unit/test_workstation_proxy.py` and verify successful tests and no new profile schema.

### 2. Provide the installed helper and split backend actions

- [ ] In `tests/unit/test_workstation_setup.py` and a focused installer-helper test, add failing tests for the [helper contract](contracts/installer-setup.md), including malformed input, sanitized exceptions, no stdout secret, saved profile on startup failure, no synthetic provider probe, and explicit stage reporting when provisioning fails after startup.
- [ ] Register hidden Windows installed-only operations under `setup` in `src/engineering_memory/cli/setup.py`. Reuse existing stack check, startup and provisioning functions with no prompts in helper mode. Keep the terminal opt-in provider probe in its current place. Check setup environment overrides without echoing their values. A start operation reads the saved profile after the inbound installer values have been discarded.
- [ ] Run `uv run pytest tests/unit/test_workstation_setup.py tests/unit/test_workstation_lifecycle.py tests/unit/test_workstation_proxy.py` and the new helper test. Verify the terminal flow still offers optional agent setup and history import.

### 3. Integrate the wizard and package smoke

- [ ] Extend `tests/structure/test_workstation_release.py` to pin normal interactive page registration, silent guards, password masking, absence of the former automatic console action, and authorization gating. Extend the Windows release smoke step to test a silent install with /LOG, verify CLI availability and verify that a fresh test profile was not created by setup.
- [ ] In `packaging/workstation/windows.iss`, create the page after file installation and before Finish so the installed onedir executable can load its runtime. Load the redacted settings via the helper. Display save, deferral and startup states. Gate startup on an unchecked-by-default consent control and a successful save. Offer an explicit retry without requiring key re-entry after a successful save. Keep package installation usable if profile setup is deferred or fails.
- [ ] Build with the repository release recipe and pinned ISCC. Verify the process identity and password transport against the actual bundled executable. Run the structure test and exercise [quickstart.md](quickstart.md) on Windows including high DPI, shell silence, and accessible keyboard traversal.
- [ ] Update `docs/operations/workstation-install.md` with the in-installer path, prerequisites, consent, saved-key behavior, retry and CLI fallback. Run `uv run ruff check .` and the repository CI checks. Record sanitized acceptance evidence before review.

## Review focus

- Old provider IDs and optional blank base survive without prefix or preset rewriting.
- Malformed, concurrently edited and interrupted profiles fail safely and do not lose #107 settings.
- Unicode input, literal special characters in a synthetic key, and missing Docker work with the compiled installer.
- Backend startup and bank failures are distinguished, with no duplicated provisioning side effects on retry.
- `/SILENT` and `/VERYSILENT` skip every helper call. A normal unelevated interactive launch uses the signed-in user's profile.

## Approval gate

Resolve fresh-provider preselection in [spec.md](spec.md) and approve this plan before generating tasks or implementing.
