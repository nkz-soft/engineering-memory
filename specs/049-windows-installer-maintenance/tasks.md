# Tasks: Windows Installer Maintenance

**Input**: [plan.md](plan.md), [spec.md](spec.md), [maintenance contract](contracts/maintenance.md)

## Phase 1 — Setup

- [x] T001 Prepare the pinned compiler and confirm the workstation baseline with `tests/structure/test_workstation_release.py`.

## Phase 2 — Foundation

- [x] T002 Write and run failing tests for deterministic manifests, version validation and changed payloads in `tests/structure/test_windows_build_identity.py`.
- [x] T003 Generate the canonical Windows manifest in `packaging/workstation/windows_manifest.py` and wire it into `packaging/workstation/build.py` and `.github/workflows/release.yml`.

## Phase 3 — User Story 1 (P1)

- [x] T004 Write and run failing maintenance regressions for an unchanged install and pre-apply cancellation in `packaging/workstation/test-windows-maintenance.ps1` and `tests/structure/test_workstation_release.py`.
- [x] T005 Route identical builds through staged settings and MCP selection in `packaging/workstation/windows.iss`.

## Phase 4 — User Story 2 (P2)

- [x] T006 Write and run failing compiled installer checks for numeric updates, downgrade, same-version replacement and damaged payloads in `packaging/workstation/test-windows-maintenance.ps1`.
- [x] T007 Implement evidence verification, update and recovery dispatch in `packaging/workstation/windows-maintenance.iss` and `packaging/workstation/windows.iss`.

## Phase 5 — User Story 3 (P3)

- [x] T008 Exercise both silent switches and compare profile, app and registry snapshots in `packaging/workstation/test-windows-maintenance.ps1`.
- [x] T009 Run the compiled Windows fixture matrix and real payload smoke in `.github/workflows/release.yml`.

## Phase 6 — Verification

- [x] T010 Document operator actions, silent outcomes and recovery in `docs/operations/workstation-install.md`.
- [ ] T011 Verify Windows desktop flows and synthetic recall using the procedure in `specs/049-windows-installer-maintenance/quickstart.md`.

Foundation precedes all stories. The installer decision and wizard share the same production script, so they are verified together before release checks.
