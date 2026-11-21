# Tasks: Windows installer configuration page

## Shared profile
- [x] T001 Verify current origin/main and the status of PR #106.
- [x] T002 Add failing profile tests in tests/unit/test_setup_profile.py.
- [x] T003 Implement shared validation and protected read/apply in src/engineering_memory/setup_profile.py.

## Interactive setup and reinstall
- [x] T004 [US1] Test and implement the Windows helper in tests/unit/test_workstation_setup.py and src/engineering_memory/cli/setup.py.
- [x] T005 [US2] Test and implement the wizard in tests/structure/test_workstation_release.py and packaging/workstation/windows.iss.

## Silent installation and CLI
- [x] T006 [US3] Exercise silent install in .github/workflows/release.yml.
- [x] T007 [US3] Document setup and recovery in docs/operations/workstation-install.md.

## Verification
- [x] T008 Run pytest, Ruff and the pinned Windows build.
- [ ] T009 Complete the clean-VM acceptance matrix in quickstart.md. See verification.md for isolated checks already run.

The shared profile precedes the helper and wizard. The guide and silent-install smoke can be updated independently once the wizard flow is set.
