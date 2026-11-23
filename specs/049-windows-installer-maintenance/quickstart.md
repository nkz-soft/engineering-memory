# Quickstart: Verify Windows Installer Maintenance

## Prepare on Windows 11 x64

1. Use a disposable regular-user profile or VM with Docker and a test model provider for the synthetic import. Keep separate snapshots for fresh, installed, legacy and damaged states.
2. Obtain Windows review artifacts from the existing **Workstation installers** workflow for the implementation revision. Prepare A and B with the same release version and different payload bytes, and C with a greater release version. Verify each SHA-256 against its workflow checksum and record the workflow run and checkout SHA. Store the assets in separate directories so same-version filenames cannot overwrite one another.
3. Record a baseline snapshot of relative payload paths and hashes, uninstaller files, the current-user uninstall entry and PATH, profile settings, archive, SQLite state, Docker volume identity and an unrelated MCP client entry. Seed a synthetic provider setup, custom ports and proxy settings, then import a synthetic conversation with a unique searchable marker. Record its document identity and provenance through the existing read-only MCP access surface. Keep credentials and profile dumps out of evidence.

## Run automated checks

From the checkout, run the existing targeted tests:

```powershell
uv sync --locked
uv run --no-sync pytest tests/structure/test_workstation_release.py tests/unit/test_workstation_setup.py tests/unit/test_workstation_settings.py tests/unit/test_workstation_lifecycle.py
```

The Windows matrix in the release workflow must compile and exercise real installers with the production decisions. Cover fresh, identical, replacement, strictly newer, downgrade, legacy and deliberately missing or modified app files. Exercise both silent switches. Assert status, manifest identity, application writes or absence, private snapshots and zero silent startup or helper activity. Use checks specific to the compiler rather than trusting a mocked setup script alone.

For manual silent spot checks, run the following once with each switch and use a distinct log for each case:

```powershell
$installer = (Resolve-Path .\engineering-memory-0.0.1-windows-x64-setup.exe).Path
$log = Join-Path $env:TEMP ("em-installer-" + [guid]::NewGuid() + ".log")
$result = Start-Process -FilePath $installer -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="' + $log + '"') -WindowStyle Hidden -Wait -PassThru
$result.ExitCode
```

Use the [maintenance contract](contracts/maintenance.md) for expected outcomes. An identical silent run must preserve the application and profile snapshots. For a blocked downgrade, compare all snapshots and check the log reason and nonzero result.

## Run desktop acceptance

1. **Install A, then rerun A.** Decline maintenance and compare snapshots. Reopen configuration, edit settings and select an MCP target, then cancel before applying and compare snapshots again. On another run save one settings change with no selected MCP changes and verify the single intended difference. Test explicit consent separately with a synthetic client profile.
2. **Run B over A.** Verify it identifies a different build at the same version. Decline once and verify zero changes. Accept replacement, defer optional configuration and startup, and verify B's installed identity and immutable payload.
3. **Run C over B.** Verify both versions are shown. Accept update and defer optional setup and startup. Compare private settings, credentials by local digest, ports, proxies, archive, SQLite, volume and MCP snapshots. Start intentionally with the normal operator command and verify the synthetic record has the same document identity and provenance. Apply the preservation checks to B as well before advancing to C.
4. **Run B over C and exercise damaged states.** Verify downgrade is blocked, including when C has a missing app file but its version is still known. In a separate snapshot remove or alter a file from the inventory and verify a suitable package offers repair rather than configuration. Confirm the successful repair reports the expected build.

Record only outcome, test command or action, artifact provenance and confirmations. See the [operator guide](../../docs/operations/workstation-install.md) for workstation startup, import and recall prerequisites.
