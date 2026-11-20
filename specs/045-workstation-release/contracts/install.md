# Installer Contract

## Windows

Start `engineering-memory-0.0.1-windows-x64-setup.exe` as the signed-in user after verifying the sidecar. The normal flow leaves the guided-setup action selected. The action invokes the installed executable with `setup --installer` as the original user. Silent installation only places the payload. Windows package success alone is insufficient evidence of backend readiness.

## Ubuntu

From a regular interactive user session run:

```bash
bash engineering-memory-0.0.1-ubuntu-amd64-install.sh ./engineering-memory_0.0.1_amd64.deb
```

Verify the launcher and package sidecars before invocation. The launcher validates its one local package argument and its matching sidecar before calling apt. A package with an unexpected package name, architecture, candidate or installed version, or an invalid checksum stops the flow. A package-manager refusal reports a failure. The launcher never forces a downgrade.

Only apt runs through sudo. Invoke `/usr/bin/engineering-memory setup` with the original terminal, account and profile after installation and version verification. Return a failure status for invalid inputs or failed package/setup execution. The wizard reports deferred setup distinctly from readiness. Users retry with the same launcher or resume the installed wizard as documented.

## Shared Outcome

Compatible Docker access is checked before provider prompts. The wizard reports a ready backend and provisioned shared bank after successful checks. Optional registration or import may be declined. Use the installed `stack status` command and inspect service state for confirmation. Failed setup must explain the stage and recovery without exposing secrets. Existing configuration and data survive reinstall.
