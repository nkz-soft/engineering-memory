# Packaging Research

## Windows and Linux formats

Use PyInstaller one-directory mode on each target. Build the Linux payload on
Ubuntu 24.04 LTS, the sole initial Linux target. PyInstaller relies on the
system glibc and recommends building on the oldest supported distribution.
One-directory mode makes the bundled libraries and product resources
inspectable and supports ordinary console launching for stdio MCP.

Use Inno Setup in non-administrative mode for per-user install and command
discovery. Use a DEB for system-wide installation on the supported Ubuntu
release. Keep per-user configuration and writes outside the package manager's
file list. Pin the build tools and Python patch version, lock dependencies, and
record versions used for each release.

Alternatives considered include a self-extracting runtime, which introduces
another extraction and startup path for every MCP launch, and a standalone
archive, which adds manual command discovery and replacement steps. A
container-only CLI would reuse more of the existing product Compose file but
would add Docker startup to every CLI and MCP launch. The selected split keeps
the installed CLI on the host and the current backend runtime in Docker.

- [PyInstaller platform notes](https://pyinstaller.org/en/stable/usage.html#platform-specific-notes)
- [Inno Setup PrivilegesRequired](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm)
- [Compose project names](https://docs.docker.com/compose/how-tos/project-name/)

## Release sequence

Build a preview on the implementation branch for clean-machine acceptance.
Build again from the approved merged tag and verify those exact candidate
assets before promoting a draft. Retain the semver version in the wheel
metadata and reject a tag that differs from the installed metadata.
A release is repeatable from the pinned source and toolchain. SHA-256
certifies individual downloaded bytes.
