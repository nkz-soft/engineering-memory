# Implementation Plan: Refresh deployment and development dependencies

**Branch** `030-refresh-dependencies` | **Date** 2026-11-05 | **Spec** [spec.md](spec.md)

## Summary

Refresh the deployment pins, Spec Kit assets, CI tooling and compatible Python dependencies. Establish current behavior with the existing checks, add focused checks before changing behavior where current checks leave gaps, and record upgrade evidence on the PR.

## Technical Context

| Area | Target |
| --- | --- |
| Hindsight shared service | `1.2.0@sha256:19d0c08f3df79acac29384826419a1ca158129e81ec527cdcbd8c97ff4ef76da` |
| LiteLLM product Compose | `v1.108.0@sha256:c560d317136880ea92d62334d4367ab10955b1af189dd3ea24f6551290b1d6c1` |
| Spec Kit | v1.3.0, sequential numbering, Claude skills and PowerShell |
| CI | checkout v7.0.1 and setup-uv v10.3.3, subject to runner compatibility |
| Runtime and tooling | Python 3.13.18 and uv 0.13.7 from the issue audit, subject to supported image and runner availability |
| Python dependency candidates | OpenTelemetry API/SDK 1.45.2, Pydantic 2.14.3, pydantic-settings 2.16.2, SQLAlchemy 2.1.8, Typer 0.27.3, pytest 9.2.0 and Ruff 0.17.3 |

## Constitution Check

| Principle | Plan compliance |
| --- | --- |
| I. Raw archive | Preserve the archive as the source of truth. Use disposable Hindsight state for upgrade validation and the existing import-to-recall check for the archive path. |
| II. Provenance and identity | Retain the live contract and import checks for metadata, tags, document identity and repeated imports. |
| III. Test-first | Run existing checks for a baseline. For behavioral or structural changes, exercise focused assertions against the old setup, observe the expected failure, then repeat against the upgrade. Run the live contract on the running candidate. |
| IV. Replaceable boundaries | Keep Hindsight behind the existing memory adapter and verify the existing access path and proxy configuration. |
| V. Secret protection | Use synthetic conversation data, redacted scanner output, and credentials supplied through the existing environment mechanism. Preserve full-history scanning and its finding control. |

The design changes versions and generated tooling within the fixed stack. No constitution deviation or decision record is required.

## Project Structure

- `deploy/hindsight/service.yaml` and `deploy/product/compose.yaml` hold the image references. Existing Compose overlays and live harnesses exercise the deployment paths.
- `.specify/` and the generated `.claude/skills/speckit-*` hold the tracked Spec Kit integration. Preserve custom workflow skills and repository settings during migration.
- `.github/workflows/ci.yml`, `.python-version`, `Dockerfile`, `pyproject.toml` and `uv.lock` govern the toolchain and dependency resolution.
- `tests/structure/` and the existing live Hindsight tests cover deployment, packaging and scanning invariants.

## Implementation and Verification

1. Check upstream migration notes and image manifest platforms. Establish a disposable 1.1.0 baseline with a known retained fact and a reusable copy of its state. Update the pins, validate the Compose configurations, and exercise clean and upgraded deployments as described in [quickstart.md](quickstart.md).
2. Install Specify v1.3.0 in an isolated environment and generate its migration diff in a scratch checkout. Compare tracked assets with the baseline, merge project customizations deliberately, and run a scratch feature through specification, plan and task generation. Exercise deduplication with fixture issues or a disposable repository.
3. Confirm action runtime and hosted runner requirements. Upgrade the actions and align Python and uv across CI and container builds. Keep the scan's full-history checkout and exit-42 negative control. Capture resolved tool versions and hosted CI results.
4. Resolve compatible candidates with uv, reviewing transitive changes and recording concrete reasons for holdbacks. Run locked sync, lint, format, tests and the image build and smoke test. Review the final diff for unintended generated changes and attach the verification evidence to the PR.

## Alternatives Considered

- Floating image tags would allow upstream changes to alter upgrade results. Keep the requested release tags and manifest digests.
- Reinitializing Spec Kit over the working repository would make overwrites harder to isolate. Generate the candidate assets in a scratch checkout and review the diff before applying them.
- An unrestricted lock refresh would mix unrelated updates into the compatibility review. Start with the audited direct dependencies and accept transitive changes needed to resolve them.

## Design Review

Existing data models and external interfaces apply. Validate their compatibility through the existing contracts. [Research decisions](research.md) and the [validation guide](quickstart.md) record the upgrade checks. The constitution check still holds after design review.
