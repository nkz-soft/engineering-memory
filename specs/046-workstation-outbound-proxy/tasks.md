# Tasks: Workstation outbound HTTP(S) proxy

## Setup and foundation

- [x] T001 Verify main and #106 and resolve the existing worktree using `.specify/scripts/powershell/setup-tasks.ps1`.
- [x] T002 Add failing profile, lifecycle, probe and packaging tests in `tests/unit/test_workstation_proxy.py` and `tests/structure/test_workstation_release.py`.

## US1 — Configure provider egress

- [x] T003 [US1] Add validated private proxy inputs in `src/engineering_memory/setup_profile.py`.
- [x] T004 [US1] Apply the LiteLLM-specific overlay in `src/engineering_memory/cli/stack.py`, `deploy/workstation/compose.proxy.yaml` and `packaging/workstation/build.py`.
- [x] T005 [US1] Offer a bounded, sanitized route check in `src/engineering_memory/cli/setup.py`.

## US2 — Change or remove the route

- [x] T006 [US2] Verify Keep, Set, Clear, cancellation and legacy behavior in `tests/unit/test_workstation_proxy.py`.

## US3 — Identify the correct setting

- [x] T007 [US3] Document URL formats, reachability, bypass and update controls in `docs/operations/workstation-install.md`.

## Verification

- [x] T008 Run unit, structure, lint and formatting checks and record results in `specs/046-workstation-outbound-proxy/verification.md`.
- [ ] T009 Run installed Windows and Ubuntu acceptance described in `specs/046-workstation-outbound-proxy/quickstart.md`.
- [x] T010 Review and publish the change with the verification results in `.github/pull_request_template.md` format.

T002 precedes product changes. T003 supplies the settings used by T004 and T005. T006 exercises those paths. T007 can be written alongside them. T008 and T009 can run independently once implementation is available.

Both packaged payloads passed the guided proxy cycle. T009 remains open for the final installer-flow run described in [verification.md](verification.md).
