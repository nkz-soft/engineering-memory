# Import coding-agent sessions automatically

Use the CLI to scan your Codex and Claude Code history after the workstation
backend is running and the memory bank has been provisioned. The command runs
once and exits, so you can run it yourself or schedule it. Installation and
guided setup leave scheduling off.

## Choose source directories

Add either or both roots to your private `app.env` if you use the workstation
package, or to the checkout's `.env` for a source installation. Use absolute
paths. If you use custom Codex or Claude Code profiles, use their actual
`sessions` or `projects` directories.

```dotenv
ENGINEERING_MEMORY_SESSION_IMPORT__CODEX_ROOT=/home/example/.codex/sessions
ENGINEERING_MEMORY_SESSION_IMPORT__CLAUDE_CODE_ROOT=/home/example/.claude/projects
ENGINEERING_MEMORY_SESSION_IMPORT__QUIET_SECONDS=300
```

On Windows use paths such as `C:/Users/example/.codex/sessions` and
`C:/Users/example/.claude/projects`. Codex is scanned at the root and in
`year/month/day` directories. Claude Code is scanned at the root and directly
inside each project directory. Secondary agent files, symlinks and junctions are
excluded. The format support is the same as for
[Codex snapshots](../codex.md) and [Claude Code snapshots](../claude-code.md).

Run once from the same account that will run the schedule.

```text
engineering-memory import-sessions --json
```

A file becomes eligible after the configured period without a write. The
command checks the file before and after reading one in-memory copy. A session
that resumes after the quiet period can be imported again when it settles.
Changed content updates the same document. The shared import state skips
extraction for unchanged content. Native files are left untouched.

The report counts imported, unchanged, deferred and failed candidates for each
source. Check the configured directory if the source is unavailable. A failure
returns a nonzero exit code while keeping successful imports. Deferred files
are scanned again next time. For a settled, malformed file, check that it uses
a supported format before retrying. An overlapping `import-sessions` run for
the same import-state path reports busy. Avoid running a separate manual import
of the same histories while a scheduled run is active.

## Windows Task Scheduler

Create a task under your own user account. Configure a trigger at logon that
repeats every 15 minutes for as long as that session runs, or choose an
interval that suits your workstation.

- Use **Run only when user is logged on** so the task uses your normal profile.
- In **Actions**, select **Start a program**. Use the installed executable
  path from `(Get-Command engineering-memory).Source` and the arguments
  `import-sessions --json`. For a source checkout, use the virtual
  environment's executable and set **Start in** to that checkout.
- In **Settings**, select **Do not start a new instance** if the task is
  already running. Use **Run** to verify the task and inspect **Last Run
  Result**. Run the command directly to see the per-source report when a task
  fails. Disable the task to stop scheduled imports.

[Microsoft Task Scheduler command reference](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-create)

## Ubuntu systemd user timer

Create the following files under `~/.config/systemd/user/` as your own user.
For a source checkout, use the executable from that checkout's virtual
environment in `ExecStart`.

`engineering-memory-import-sessions.service`

```ini
[Unit]
Description=Import local coding-agent sessions

[Service]
Type=oneshot
ExecStart=/usr/bin/engineering-memory import-sessions --json
```

`engineering-memory-import-sessions.timer`

```ini
[Unit]
Description=Import local coding-agent sessions every 15 minutes

[Timer]
OnStartupSec=5min
OnUnitInactiveSec=15min

[Install]
WantedBy=timers.target
```

```sh
systemctl --user daemon-reload
systemctl --user start engineering-memory-import-sessions.service
systemctl --user enable --now engineering-memory-import-sessions.timer
systemctl --user list-timers engineering-memory-import-sessions.timer
journalctl --user -u engineering-memory-import-sessions.service
```

Stop and disable the timer with
`systemctl --user disable --now engineering-memory-import-sessions.timer`.
The timer runs while the systemd user manager is active.

[systemd timer reference](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html)
