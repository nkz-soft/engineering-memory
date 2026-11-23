# Implementation Plan: Inline MCP Setup Results on Windows

**Branch** `050-windows-mcp-inline-results` | **Date** 2026-11-23 | **Spec** [spec.md](spec.md)

## Summary

Capture an ordered batch of selected reviews in the Windows wizard. Run each target using its original review token and decision, then display registration and local MCP check outcomes independently. Keep the results on the page and allow an explicit retry or continuation.

## Technical Context

Existing Inno Setup 6.5.4 Pascal Script on Windows x64, and the frozen Python 3.13 helper with its current `EM-MCP1` scan and apply protocol. Keep page state in memory and let the existing helper own client file writes, revalidation and local MCP probes. Use the existing packaged Windows test infrastructure and pytest coverage of the helper. The scan currently supports at most four rows. One pass invokes the existing helper once per selected eligible row, plus a scan when requested.

## Constitution Check

| Principle | Compliance |
| --- | --- |
| I. Raw archive | The wizard continues to configure client profiles only. |
| II. Provenance and stable identity | History IDs and metadata stay under the existing pipeline. Use a profile key for UI reconciliation and the existing snapshot token for authorization. |
| III. Test-first | Observe the compiled multi-selection regression failing on the current wizard before fixing it. Prove the red test reaches a progress-page return. |
| IV. Replaceable boundaries | Keep the wizard behind the existing installer helper interface and client access on the existing local stdio MCP server. |
| V. Secrets | Display decoded, safe helper diagnostics only. Do not publish profile contents, review tokens or raw subprocess output. Use synthetic fixtures for automation. |

The pre-research and post-design checks pass. No constitution or architecture decision changes.

## Project Structure

| Path | Responsibility |
| --- | --- |
| `packaging/workstation/windows.iss` | Profile rows, selection snapshot, check and rescan events, progress, results and maintenance navigation. |
| `packaging/workstation/test-windows-mcp.ps1` | Compile the wizard with isolated fixture profiles and drive the interactive regression on a Windows desktop. |
| `packaging/workstation/test-windows-maintenance.ps1` and `.github/workflows/release.yml` | Reuse pinned compiler and fixture packaging conventions, preserve the silent maintenance matrix, and invoke the interactive regression on a Windows runner if a usable desktop is available. Keep the desktop test runnable directly. |
| `tests/unit/test_workstation_setup.py`, `tests/unit/test_setup_clients.py` | Existing helper protocol, profile safety, registration and diagnostic regression checks. |

## Implementation and Verification Sequence

1. **Reproduce the reset (FR-001, SC-001/004).** Start with the compiled wizard and isolate helper replies behind fixture inputs. Select Codex and Claude Desktop and leave Claude Code unchecked. Drive the real click and wait for the first progress page to hide. Assert two recorded apply requests in order with correct tokens, the expected Claude Desktop fixture write, and untouched Claude Code. Observe the missing second request on the baseline. Repeat with a failing first response. Use the same fixture and assertions for the fixed flow.
2. **Capture and apply exact reviews (FR-001, FR-005/006).** Parse scan output into complete records before publishing it. Create immutable attempt values before confirmations, writes or progress transitions. Bind a replacement decision to the captured review; pass the original token into `ApplyMcpTarget`. Keep busy state through `ProgressPage.Hide` and guard the MCP branch in `CurPageChanged`. Assert decline, acceptance, stale token, malformed helper response and continuation after failure.
3. **Present and retry (FR-002–004, FR-006).** Add **Check selected clients** and **Rescan** controls. Keep a result per row, update the inline status and focused details, and keep ordinary navigation separate. Explicit rescan joins rows by the profile key described in [data-model.md](data-model.md). Clear changed selections, invalidate consent, and require a fresh action. Test retry of the same saved profile without another configuration write, focus/status changes, explicit continuation, and persistence of restart and `service_tier` guidance.
4. **Preserve installer modes (FR-007).** On maintenance check, keep the existing installation revalidation, overall confirmation for pending changes and settings save before helper apply. On maintenance navigation, apply only pending settings through the same guards. Keep discard/cancel behavior for unapplied edits and existing silent paths. Cover both wizard entry points and run [quickstart.md](quickstart.md), including acceptance with real client profiles.

## Design References

- [Research and alternatives](research.md)
- [Data model and state transitions](data-model.md)
- [Windows wizard contract](contracts/windows-mcp-page.md)
- [Verification guide](quickstart.md)
