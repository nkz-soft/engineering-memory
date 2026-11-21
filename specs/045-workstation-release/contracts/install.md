# Installer Contract

## Windows

Start `engineering-memory-0.0.1-windows-x64-setup.exe` as the signed-in user after verifying the sidecar. The installer opens the [embedded configuration page](../../047-windows-setup-ui/spec.md) after copying files. Save the profile and opt in to starting the stack and provisioning the shared bank. Silent installation skips configuration and preserves existing settings. Windows package success alone is insufficient evidence of backend readiness.

## Ubuntu

From a regular interactive user session run:

```bash
bash engineering-memory-0.0.1-ubuntu-amd64-install.sh ./engineering-memory_0.0.1_amd64.deb
```

Use a download directory writable only by your account. Verify the launcher and package sidecars before invocation. The launcher validates its one local package argument and its matching sidecar before calling apt. A package with an unexpected package name, architecture, candidate or installed version, or an invalid checksum stops the flow. A package-manager refusal reports a failure. The launcher never forces a downgrade.

Only apt runs through sudo. Invoke `/usr/bin/engineering-memory setup` with the original terminal, account and profile after installation and version verification. Return a failure status for invalid inputs or failed package/setup execution. The wizard reports deferred setup distinctly from readiness. Users retry with the same launcher or resume the installed wizard as documented.

## Shared Outcome

Ubuntu checks Docker access before provider prompts. Windows checks Docker access after the user elects to start the stack. The wizard reports a ready backend and provisioned shared bank after successful checks. Optional registration and import are offered by terminal setup and can be deferred. Use the installed `stack status` command and inspect service state for confirmation. Failed setup must explain the stage and recovery without exposing secrets. Existing configuration and data survive reinstall.
