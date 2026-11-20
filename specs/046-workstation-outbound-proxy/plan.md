# Implementation Plan: Workstation outbound HTTP(S) proxy

**Branch**: `046-workstation-outbound-proxy` | **Date**: 2026-11-20 | **Spec**: [spec.md](spec.md)

## Summary

Add optional outbound proxy routing to installed guided setup. Store the route in the protected workstation Compose profile, apply it to LiteLLM on stack start, and offer a sanitized provider-route check. Preserve the provider API base and the local stack path.

## Technical Context

- **Runtime and dependencies** — Python 3.13, Typer, HTTPX and the pinned LiteLLM image. Reuse the existing Docker Compose and PyInstaller packaging.
- **Storage** — Existing private `compose.env`, with the workstation profile lock, ACL or Unix permissions, atomic write and recovery journal.
- **Target** — Installed executable and bundled Linux containers on Windows and Ubuntu. Scope covers one workstation profile and its LiteLLM provider route.
- **Testing** — pytest unit/structure coverage and a controlled installed acceptance run on each platform. Bound the route check and preserve existing backend readiness semantics.

## Base and release dependency

The verified `origin/main` was `1cd74e5d2b38c145ea6bcef4ee4488f0117971fd` at planning. [#105](https://github.com/nkz-soft/engineering-memory/issues/105) and [PR #106](https://github.com/nkz-soft/engineering-memory/pull/106) were open. PR #106 at `9b6c144` adds the Ubuntu release installer and touches `cli/setup.py`, `cli/stack.py`, tests and the workstation guide. Spec Kit generated this branch with feature number 046 to leave 045 available for #105. Before Phase 2, refresh main and verify that the Ubuntu installer and the relevant setup and stack changes from #106 are present. Rebase the spec-only branch on that main and reconcile touchpoints. If #106 has not landed, keep the Ubuntu installed acceptance gate pending and reassess against its actual disposition.

## Constitution Check

Initial and post-design checks pass. No deviations or governance changes are required.

| Principle | Application |
| --- | --- |
| I. Raw archive | Workstation network configuration and synthetic probes are outside ingestion. The archive remains authoritative. |
| II. Provenance and identity | The probe creates no retained items. IDs, provenance, timestamps and deduplication remain on their existing paths. |
| III. Test-first | Start each behavior change with a failing test. Require observed installed acceptance evidence before marking the feature verified. |
| IV. Replaceable boundaries | Keep transport configuration in installed setup, stack, and LiteLLM Compose configuration. The ingestion, memory store and read-service interfaces are preserved. |
| V. Secrets | Reuse protected profile storage and inject secrets only into LiteLLM's environment. Preserve quiet Compose checks, disable service logging as today and return allowlisted diagnostics. Keep test evidence synthetic and sanitized. |

## Project Structure

Planning artifacts are [research.md](research.md), [data-model.md](data-model.md), [contracts/setup.md](contracts/setup.md), [quickstart.md](quickstart.md) and the [requirements checklist](checklists/requirements.md).

- `src/engineering_memory/setup_profile.py` owns collection, validation and profile updates. `cli/setup.py` offers the route check after successful stack start and before subsequent setup stages.
- `src/engineering_memory/cli/stack.py` and `settings.py` resolve the private route and build a consistent Compose invocation. `deploy/workstation/compose.yaml` is the base. Package an opt-in LiteLLM override under `deploy/workstation/` through `packaging/workstation/build.py` and verify it is shipped in both installers.
- Extend `tests/unit/test_workstation_setup.py`, `test_workstation_lifecycle.py`, `test_workstation_settings.py` and `tests/structure/test_workstation_release.py` where the existing boundaries fit. Document operator steps in `docs/operations/workstation-install.md`.

## Implementation sequence after approval

1. Cover missing values, Keep/Set/Clear, validation, hidden input, cancel and rollback. Add the optional profile fields via the existing protected transactional writer.
2. Cover Compose configuration and container recreation for set/change/clear, including ambient environment and Docker client proxy defaults. Add a static bundled override selected consistently for all stack commands when the profile manages routing. Use namespaced interpolation keys and set both cases of the standard proxy variables in LiteLLM. Clearing all managed fields restores the base configuration on the next Compose up. Check that the existing provider base, credentials and local paths are preserved.
3. Cover safe local probe success, timeout, invalid or rejecting proxy, and provider failures. Send one bounded synthetic completion via loopback with ambient proxy disabled, read only enough to classify success/failure, and emit fixed operator guidance. Offer the check explicitly before any history import. Keep stack readiness checks independent of provider availability.
4. Verify override packaging, update the guide and execute the controlled matrix in [quickstart.md](quickstart.md) on Windows and Ubuntu. Capture redacted evidence and run targeted pytest, Ruff, and the repository's normal CI checks before review.
