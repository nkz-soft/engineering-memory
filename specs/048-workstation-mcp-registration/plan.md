# Implementation Plan: Workstation MCP Registration

**Branch**: `048-workstation-mcp-registration` | **Date**: 2026-11-21 | **Spec**: [spec.md](spec.md)
**Input**: [Issue #109](https://github.com/nkz-soft/engineering-memory/issues/109) and the built-in Windows wizard shipped in #111.

## Summary

Use one current-user registration workflow for the interactive Windows installer, Ubuntu launcher and standalone setup. Discover installed clients independently, map each to its effective user configuration, and run consent, mutation and local verification once per configuration. Keep interaction in the installer or terminal and registry/profile logic in Python.

## Technical Context

| Area | Plan |
| --- | --- |
| Runtime and packaging | Python 3.13, uv, Typer, official MCP SDK with AnyIO, PyInstaller, Inno Setup 6.5.4 and DEB |
| Client storage | Codex TOML and Claude JSON under proven current-user targets. Use a version-locked round-trip TOML editor (`tomlkit`) for the client file only |
| Platforms | Windows 11 x64 and Ubuntu 24.04 LTS amd64. Run CI on `windows-2025` and `ubuntu-24.04` x64. Confirm Windows desktop UX on Windows 11 |
| Verification | pytest, existing packaging smoke and installer fixtures, authenticated manual checks after implementation |
| Time and privacy | 30-second total handshake deadline per profile, one known installed binary, offline scratch profile, no tool calls or user history access |

## Constitution Check

| Principle | Design and implementation check |
| --- | --- |
| I. Raw Archive Is the Source of Truth | Install only an access registration. The probe uses isolated empty scratch paths and existing import preserves the archive contract. |
| II. Provenance and Stable Identity | Tool discovery keeps the existing access API. Neither registration nor its probe changes documents, references or timestamps. |
| III. Test-First | Observe red before each behavior change. Keep the isolated platform fixtures and compiled installer checks as regression tests. |
| IV. Replaceable Boundaries | Keep client adapters at workstation setup. Reuse the stdio command and SDK; access continues through the existing memory interface. |
| V. Secrets Never Reach the Memory Engine | Probe with an allowlisted runtime environment and scratch config, with no live profile, tool calls or history. Emit fixed statuses only. |

The post-design check finds no principle deviations. The TOML editor is a proposed installer dependency for lossless editing. It adds a file-format capability without replacing a stack entry. No governance decision record is required by the issue.

## Project Structure

| File or directory | Responsibility |
| --- | --- |
| `src/engineering_memory/setup_clients.py` | Discovery, target grouping, inspection and guarded single-entry updates. Keep profile discovery separate from history sources |
| `src/engineering_memory/setup_mcp_probe.py` | Bounded stdio probe of the installed binary |
| `src/engineering_memory/settings.py`, `setup_profile.py` under the same package | Reuse profile resolution, sanitized launch environment and atomic file-write primitives where their contracts fit |
| `src/engineering_memory/cli/setup.py`, `packaging/workstation/windows.iss` | Terminal interaction and Inno wizard request/response handling |
| `packaging/workstation/install-ubuntu.sh` | Preserve normal installer's existing guided setup entry point and exercise it in integration tests |
| `pyproject.toml`, `uv.lock`, `packaging/workstation/` | Pin the TOML helper and verify it is present in the frozen installer |
| `tests/unit/test_setup_clients.py`, `tests/unit/test_setup_client_discovery.py`, `tests/unit/test_setup_mcp_probe.py`, `tests/unit/test_workstation_setup.py`, `tests/structure/` | Discovery matrix, round-trip edits, bounded probe, UI helper and packaging regressions |
| `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `docs/operations/workstation-install.md` | Required PR discovery gate, review installer builds from existing release packaging steps, restart and diagnostics documentation |

## Implementation and verification sequence

1. **Discover installations and resolve profiles (FR-001–002, FR-008).** Provide discovery with injectable install evidence roots, environment and Windows package queries. Use the same production decision logic on real runners with isolated inputs. Do not probe arbitrary commands, treat profile residue as installation, or conflate Desktop's embedded CLI with a separately installed CLI. Confirm package IDs, path precedence and override behavior against vendor metadata or the app's configuration UI before fixing fixture expectations. Assert exact identities, file paths, grouped members and zero writes to unselected or ineligible targets.
2. **Inspect and persist one target (FR-003–005).** Use round-trip TOML for Codex and strict JSON for Claude. Avoid a whole-document TOML rewrite. Preserve unrelated TOML settings and comments, unrelated JSON values and entries, and leave matching files byte-identical. Parse and validate the candidate before an atomic replacement that retains existing access restrictions. Serialize installer writes to the same target, recheck original bytes and path identity immediately before replacing, and reject redirected or ambiguous targets. Scope confirmation to the inspected snapshot. Distinguish the Codex registration parse from client-version schema validation; preserve `service_tier` and explain when the installed CLI may reject it. Test quoted and dotted TOML forms, malformed or duplicate keys, JSON unrelated values, disabled and alternate transports, Unicode paths, replacement decline, stale consent, competing setup or external edits, failed writes and idempotency.
3. **Verify persisted entries (FR-006–007).** Re-read the resolved profile after selection, including a selected match. Launch only the absolute installed executable with `serve`, starting from private scratch config, data, cache and working directories with synthetic loopback settings. Use explicit initialization via the SDK session, then list tools within one deadline, with bounded failure and teardown even for a hung child. Suppress raw output, validate both tool names, and never invoke a tool. Test failed initialization, missing tools, timeout and cleanup, spawn failure and a discrepant read-back, plus a successful packaged binary probe.
4. **Connect user interfaces (FR-003–007).** Extend #111's current-user installer helper with explicit scan/apply actions and an Inno registration step after payload copy. Show client names and target state, leave selection off by default, and ask separately to replace conflicts. Send only selected target identity and snapshot authorization via the existing protected helper pattern. Preserve Windows elevation/silent behavior and startup choices. In Ubuntu's existing regular-user guided flow and standalone setup, offer registration even when other stages are deferred, without triggering startup or import. Add fixture coverage for normal interactive install, opt-out, silent install, no clients, refusal and retry.
5. **Require CI and deliver the acceptance build (FR-008–009).** Run the dedicated discovery tests on every PR in a two-platform matrix. Use a stable required check named `Workstation client discovery` that always runs and succeeds only when both matrix legs succeed. Use GitHub's ruleset on `main` to make this check a merge requirement once the workflow reports it. The currently active ruleset does not enforce required status checks. Treat configuring the rule and verifying a failing result blocks a PR as acceptance work with repository administration access. Reuse release build and smoke steps for the implementation commit, and publish a review-run Windows installer and Ubuntu DEB/launcher with SHA-256 sums, build run, exact SHA and smoke results. Keep pre-approval work at documentation.

## Discovery CI acceptance

| Fixture family | Assertions |
| --- | --- |
| All subsets independently on each runner | 16 cases per platform. Empty set, four singletons, every pair and triple, all four. Includes both desktops only, both CLI only, same-vendor pairs and mixed vendors |
| Windows variants | Native/installed CLI and npm shim/native payload, Codex Desktop current-user package, Claude Desktop roaming and MSIX incl. `Claude-3p`, and coexistence or ambiguous evidence |
| Ubuntu variants | Native/PATH CLI, vendor Desktop DEB install signals, default and proven custom XDG layouts |
| Custom and overlapping profiles | Default and custom Codex/Claude Code roots, shared versus distinct Codex files, and correct Claude Code vs Claude Desktop separation |
| Negative cases | Residual profiles, other users, app-only helper binaries, missing shim payload, unsupported packaging and stale/conflicting markers. Compare exact safe outcomes and assert no creation/writes |

## Alternatives considered

- **Use client commands for every change.** Current CLI integration supports some cases, but requires executable availability and successful full-profile validation. Desktop-only and the known Codex version mismatch need a profile path.
- **Move MCP setup into a separately launched terminal.** That would bypass #111's ordinary Windows wizard and add another process and prompt experience for desktop users.
- **Use a shared engine and profile adapters.** Chosen for both UIs. A lossless TOML editor is preferable to a hand-written parser for dotted keys, inline tables and comments. An intentionally small JSON update and safe failure behavior cover the Claude profiles.

See [research.md](research.md) for evidence, [data-model.md](data-model.md) and [registration contract](contracts/registration.md) for the flow, and [quickstart.md](quickstart.md) for validation.
