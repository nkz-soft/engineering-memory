# Release Packaging Decisions

## Ubuntu user handoff

Use a Bash launcher that calls apt with sudo only for package installation. The package remains usable as a conventional Debian package. The launcher owns the interactive transition to the signed-in user. A Debian post-install maintainer script runs during package management with elevated privileges and cannot rely on the intended user's interactive terminal. The existing setup also rejects root. Running a separate setup command after apt would keep the current gap.

## Windows user handoff

Use the existing Inno Setup post-install action with `runasoriginaluser`. Keep silent installation for CI and automation. Interactive acceptance must actually observe the console wizard, readiness and provisioning. The current smoke tests prove CLI version, offline status and MCP transport.

## Prerequisites and readiness

Reuse the workstation CLI's Docker probes and perform them before asking for provider inputs. Keep Docker itself a documented system dependency. The setup command already starts Compose with a bounded readiness wait and provisions the shared bank before optional import. An unavailable Docker engine or test provider blocks live acceptance.

## Release artifacts

Extend the existing tag-to-draft workflow and lockfile discipline. Integrity verification binds acceptance to the exact draft bytes. A successful package-only build provides a prerequisite for live workstation acceptance.
