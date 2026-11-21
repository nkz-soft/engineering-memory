# Tasks: Workstation Release v0.0.1

## Phase 1 — Release identity

- [x] T001 Cover version, workflow asset and tag agreement in `tests/structure/test_workstation_release.py`.
- [x] T002 Align `pyproject.toml` and `uv.lock` on `0.0.1`.

## Phase 2 — User Story 1, install and start

- [x] T003 [US1] Cover Docker preflight ordering and early failure in `tests/unit/test_workstation_setup.py`.
- [x] T004 [US1] Reuse Docker preflight before setup prompts in `src/engineering_memory/cli/stack.py` and `src/engineering_memory/cli/setup.py`.
- [x] T005 [US1] Test the Ubuntu installer handoff and failure paths in `tests/structure/test_ubuntu_installer.py`.
- [x] T006 [US1] Implement `packaging/workstation/install-ubuntu.sh` and integrate it with the build and smoke tests in `.github/workflows/release.yml`.

## Phase 3 — User Story 2, verify and recover

- [x] T007 [US2] Update release instructions and recovery in `docs/operations/workstation-install.md` and `README.md`.
- [x] T008 [US2] Run regression and packaging checks and record the results in `specs/045-workstation-release/verification.md`.

## Phase 4 — User Story 3, verify release assets

- [x] T009 [US3] Verify the draft asset manifest and checksums in `.github/workflows/release.yml`.
- [ ] T010 [US3] After merge, create the candidate draft, complete both interactive workstation runs and record results in `specs/045-workstation-release/verification.md`.
- [ ] T011 [US3] After both passes, publish v0.0.1 and verify the public digests against `specs/045-workstation-release/verification.md`.

Tasks T010–T011 are maintainer release steps. Real Claude Code and Codex acceptance is tracked by #71 after workstation installation.
