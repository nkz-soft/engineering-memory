# Workstation Release Verification

## Implementation checks

- `uv lock --check` with uv 0.13.7 resolved the locked project. The lockfile change updates the project version and lock format revision. Dependency versions are unchanged.
- Windows `pytest -q --basetemp <worktree scratch>` passed 2,481 tests with 103 skipped. Ubuntu-only launcher and opt-in integration cases are covered separately or remain pending as applicable.
- Ruff lint and format checks and `git diff --check` passed.
- Ubuntu 24.04 in WSL, under an unprivileged user, passed nine launcher cases with apt and the installed CLI stubbed. A separate real root invocation refused to proceed. These checks cover the handoff, invalid inputs, a newer installed version, a failed install, an incomplete installed state and setup failure.
- The packaging workflow verifies the real Ubuntu launcher reaches the installed setup under the runner's regular user. It uses a synthetic early setup failure that requires no provider credential. Windows CI exercises silent installation and the installed CLI and MCP smoke checks.

## Release acceptance

| Platform | Interactive setup | Live import and MCP | Reinstall and retry |
| --- | --- | --- | --- |
| Windows 11 x64 | Pending | Pending | Pending |
| Ubuntu 24.04 LTS amd64 | Pending | Pending | Pending |

Record the exact draft tag, revision, SHA-256 digests, platforms and outcomes using [the clean-workstation procedure](quickstart.md). Publish after both platform checks pass, then verify the public digests. Manual agent acceptance is tracked in #71.
