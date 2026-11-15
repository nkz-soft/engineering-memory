# Research: Automatic Coding-Agent Session Import

## Schedule the one-shot command

**Decision** Document operator-managed Windows Task Scheduler and a systemd user timer on Ubuntu. Run with the same installed program, operator profile and provisioned backend as the manual command.

**Rationale** Both workstation installs already expose the CLI. Running the command under the same account preserves access to native history, private settings and the existing import state.

**Alternatives considered** An in-process watcher or service would introduce a lifecycle and a second operational mechanism. Automatically registering a timer during setup would make scheduling implicit.

## Determine when to copy

**Decision** Require a configurable quiet period, defaulting to five minutes, then compare the source file identity, size and modification metadata before and after copying. Compare the bytes copied with the expected size. Parse only the private copy.

**Rationale** The supported Claude Code format has no common close marker. Codex turn completion still allows a later turn. A settled file can resume, so rescan on each run and leave deduplication to normal import state. This is a best-effort eligibility rule and does not prove that the client process closed. A settled, malformed copy is reported and remains eligible for retry.

**Alternatives considered** An end-of-session event is unavailable consistently across the two adapters. A persistent record of seen file paths would miss resumed sessions and duplicate import state.

## Keep capture within known layouts

**Decision** Use explicitly configured roots. Support the root itself and the native Codex date hierarchy and Claude Code project directories. Refuse links, junctions and unsupported nesting. Reuse the source adapters' parse and publication rules.

**Rationale** The manual adapters deliberately read a selected file or a flat export directory. Local discovery belongs upstream of those contracts. Guided setup already checks parent paths for symlinks and junctions in setup_history.py. Reuse that check where useful and keep capture-specific directory layouts independent from setup's interactive discovery. Keep I/O and format failures local to a candidate, since the current pipeline treats an unhandled source error as terminal for that source.

**Alternatives considered** Recursive discovery across arbitrary profiles could capture subagents and unrelated histories. Flattening all snapshots into one directory adds collision handling and requires staging the entire batch.

## Guard against overlapping capture

**Decision** Use a nonblocking OS-held lock keyed to the effective import-state path for capture invocations. Document that operators should avoid running a manual import of the same histories concurrently.

**Rationale** Scheduled and one-shot capture share one entry point. A lock released by the OS at process exit avoids stale ownership after termination.

**Alternatives considered** Scheduler settings alone leave manual capture unguarded. Changing the concurrency contract of every existing import entry point would expand the scope of #83.
