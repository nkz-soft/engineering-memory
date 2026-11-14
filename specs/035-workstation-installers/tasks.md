# Tasks: Workstation Installers

## Installed CLI (US1)

- [x] T001 [US1] Exercise installed config, version metadata and package layout in `tests/unit/test_workstation_settings.py` and `tests/structure/test_workstation_release.py`.
- [x] T002 [US1] Build the native payload and packages in `packaging/workstation/` and load private settings in `src/engineering_memory/settings.py`.

## Backend and recall (US2)

- [x] T003 [US2] Exercise Compose prerequisites, readiness and private configuration in `tests/unit/test_workstation_lifecycle.py`.
- [x] T004 [US2] Wire the installed stack commands and backend assets in `src/engineering_memory/cli/` and `deploy/workstation/`. Document provider and MCP setup in `docs/operations/workstation-install.md`.

## Persistence (US3)

- [x] T005 [US3] Verify package ownership and stop semantics in `tests/structure/test_workstation_release.py` and `tests/unit/test_workstation_lifecycle.py`.
- [ ] T006 [US3] Record clean platform import, recall, restart and reinstall results using `specs/035-workstation-installers/quickstart.md`.

## Release (US4)

- [x] T007 [US4] Check version guards and permissions in `tests/structure/test_workstation_release.py`. Build both platform candidates and gate the draft release in `.github/workflows/release.yml`.
- [x] T008 [US4] Record the packaging decision in `ARCHITECTURE.md` and `.specify/memory/constitution.md`.
- [ ] T009 [US4] After merge, build from v0.1.0 and verify draft and public assets as documented in `docs/operations/workstation-install.md`.
