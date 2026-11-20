# Workstation Release v0.0.1 Implementation Plan

> **For agentic workers:** Follow the approved Issue to PR workflow. Generate tasks after the planning review and use test-first implementation.

**Branch**: `045-workstation-release`
**Date**: 2026-11-20
**Spec**: [Workstation Release v0.0.1](spec.md)

## Summary

Ship the existing packaged CLI and guided setup as one interactive installation flow on both supported platforms. Reuse the Windows installer handoff and add a versioned Ubuntu launcher around the existing package. The launchers hand off to the same user-level setup and retain the current Compose deployment.

## Technical Context

- Python 3.13 and uv govern the build. Inno Setup packages Windows 11 x64. Bash, apt and dpkg package and launch Ubuntu 24.04 LTS amd64.
- Docker Engine >=28, Linux containers and Compose >=2.24.4 remain system prerequisites. Docker and compatible provider access are required for live acceptance.
- Existing workstation profile files, archive, SQLite database and Docker volumes remain in their current locations. The installer adds no data store.
- Use pytest and the existing package smoke test for automated verification. Validate the interactive journey independently with exact candidate assets.

## Constitution Check

| Principle | Design check |
| --- | --- |
| I. Raw archive | Guided import uses the existing pipeline. Reinstall leaves the raw and normalized archives readable. |
| II. Provenance and identity | Validate original time, stable document ID and unchanged-import skipping through the installed flow. |
| III. Test-first | Add targeted failing tests before changing executable behavior. Run the existing packaging, stack and setup regressions. |
| IV. Replaceable boundaries | Lifecycle stays in the workstation CLI. Installed consumers use the existing read-only stdio MCP surface. |
| V. Secrets | Existing private profile and sanitization rules apply. Package manifests, argument lists and acceptance evidence contain no credentials. |

Architecture §22 already calls for local backend setup and provisioning. Packaging adds no capability excluded by §21 and requires no constitution or ADR change.

## Implementation Sequence

### 1. Align release identity

- Start with a structural test asserting project/lock version consistency and the candidate asset contract. Update `pyproject.toml` and regenerate `uv.lock` with the pinned lock tooling while preserving dependency versions.
- Reuse the tag check in `packaging/workstation/build.py`. Confirm that the package smoke test sees `engineering-memory 0.0.1` on Windows and Ubuntu, and that a mismatched tag fails packaging.

### 2. Complete the installer handoff

- In `src/engineering_memory/cli/stack.py`, extract `check_docker()` from the existing CLI preflight and reuse it in `run_stack()` and early in `src/engineering_memory/cli/setup.py`. Keep the bounded subprocess calls, Windows bundled DLL search handling and secret-safe diagnostics. Check profile/Compose configuration after profile creation as before.
- Pin setup ordering in `tests/unit/test_workstation_setup.py`. A Docker failure occurs before provider prompts or profile writes. A failed or deferred setup never prints backend readiness or starts an import. Print the overall setup-success message only after provisioning. Keep the existing stack readiness message scoped to the services.
- Keep the checked Windows post-install `setup --installer` action in `packaging/workstation/windows.iss`, with original-user execution and silent-mode opt-out. Treat the wizard's result and the actual stack state as the readiness signal. Verify the interactive handoff on a clean Windows user account.
- Add `packaging/workstation/install-ubuntu.sh`. Its published name is `engineering-memory-0.0.1-ubuntu-amd64-install.sh`. Use the local package passed as a single argument. Use the workflow to stamp the candidate version into the published launcher. Check terminal, non-root execution, package/sidecar metadata and hash, run apt via sudo, verify the installed package version, then invoke `/usr/bin/engineering-memory setup` directly as the invoking user. See [contract](contracts/install.md).
- Test the Ubuntu launcher on the Ubuntu CI runner using a terminal with stubbed package install and setup commands. Exercise package paths containing spaces, sudo failure, version mismatch, root/non-terminal invocation and setup failure. Keep the existing installed CLI smoke test against the real package.

### 3. Build, document and accept release assets

- Extend `.github/workflows/release.yml` so Ubuntu uploads the launcher, package and their sidecars. The draft job checks the exact asset set and file-specific hashes before uploading. Keep PR runs free of release writes.
- Update `docs/operations/workstation-install.md`, its README link and release notes. Lead with the supported single-invocation path and include prerequisites, checksum verification, readiness and retry. Mark old examples in historical specs as historical or point readers to the versioned guide when appropriate.
- Run the targeted workstation tests, `uv lock --check`, `uv run --locked pytest`, and the Windows/Ubuntu packaging matrix. Then use the [candidate validation guide](quickstart.md) for live evidence and publication checks.
- Publish only after both platform records pass. Keep the manual real-agent exercise in #71 after successful installation.

## Review Focus

- A missing or stopped Docker daemon never triggers provider prompts or profile changes.
- Installing from a path containing spaces reaches the exact Ubuntu package and its matching sidecar.
- Cancellation, failed apt and an installed version mismatch never start a different CLI's setup.
- Windows silent install succeeds as a package operation and does not claim backend readiness.
- Repeated install with existing profile and Docker data preserves settings, state, the archive and retained data.

The design retains the existing package and stack boundaries. All five constitution checks still pass after design review.
