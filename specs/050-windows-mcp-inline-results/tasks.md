# Tasks: Inline MCP Setup Results on Windows

## Setup

- [X] T001 Prepare the pinned Inno Setup compiler, temporary profiles and isolated fixture installer.

## US1 — Check several clients in one pass

- [X] T002 [US1] Compile and run the regression in `packaging/workstation/test-windows-mcp.ps1`. Observe the missing second request following a progress-page return.
- [X] T003 [US1] Capture selected reviews and run the complete ordered pass in `packaging/workstation/windows.iss`, including when the first helper call fails.

## US2 — Review results and retry

- [X] T004 [US2] Assert registration and check statuses, focus diagnostics, rescan/retry and continuation in the compiled fixture.
- [X] T005 [US2] Add check and rescan controls, inline outcomes and guarded page activation in `packaging/workstation/windows.iss`.

## US3 — Control replacement and keep maintenance behavior

- [X] T006 [US3] Exercise declined, confirmed and stale reviews and maintenance navigation in the fixture.
- [X] T007 [US3] Bind consent to each attempt and preserve the existing maintenance validation, confirmation and settings save order in `packaging/workstation/windows.iss`.

## Verification

- [X] T008 Run the compiled regression, silent maintenance matrix and Python tests.
- [ ] T009 Perform the interactive real-client profile validation in `quickstart.md`.
- [X] T010 Review the changes and prepare verification evidence for the PR.
