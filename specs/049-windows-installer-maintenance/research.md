# Research: Windows Installer Maintenance

## Build identity and health

**Decision** — Hash a canonical inventory of installed payload files and bind it to the release version and packaging recipe. Compare exact build identities only for equality.

**Rationale** — `packaging/workstation/build.py` builds a PyInstaller onedir directory, and `.github/workflows/release.yml` compiles PR artifacts directly from the PR head while keeping the project version. A single executable hash would miss bundled files. Hashing the completed installer creates a circular dependency if the identity is embedded. Two builds with byte differences may legitimately have different identities even when built from one Git revision.

**Installation evidence** — The existing `AppId=EngineeringMemory`, per-user install policy and current uninstall entry identify the installation. Use the Inno uninstall entry as path and version evidence for older packages that lack a manifest. A registry entry or binary alone cannot establish health. Use Inno's built-in file SHA-256 and numeric version helpers. Test their behavior with the pinned compiler. [Inno support functions](https://jrsoftware.org/inno-setup/documentation/topic_scriptfunctions.htm) · [Numeric version comparison](https://jrsoftware.org/inno-setup/documentation/topic_isxfunc_comparepackedversion.htm)

## Configuration-only startup and silent no-op

**Decision** — Use pre-install classification and keep the built-in wizard. Gate copy, uninstall logging and registration, application restart handling and PATH updates in no-copy mode. Have silent no-op use normal successful completion and blocked operations abort before writes.

**Rationale** — The current wizard anchors settings after `wpInstalling` and updates PATH in `ssPostInstall`. Inno explicitly calls `NextButtonClick` in silent mode and does not allow skipping the preparing or installing pages with `ShouldSkipPage`. Therefore page navigation alone cannot implement a no-op. The file checks and scriptable uninstall controls provide independent guards. Verify zero filesystem and registry differences with compiled packages. [Inno setup events](https://jrsoftware.org/inno-setup/documentation/topic_scriptevents.htm) · [Files section](https://jrsoftware.org/inno-setup/documentation/topic_filessection.htm) · [Uninstallable](https://jrsoftware.org/inno-setup/documentation/topic_setup_uninstallable.htm) · [CreateUninstallRegKey](https://jrsoftware.org/ishelp/topic_setup_createuninstallregkey.htm)

## Legacy and recovery

**Decision** — Offer interactive repair for an incomplete install when reliable version evidence establishes the incoming version is equal or newer. Where version evidence is missing or contradictory, display instructions to verify the correct package and existing state before repair. Block known older packages before considering repair.

**Rationale** — The old installer does not record comparable build identity. A one-time explicit update or repair brings it into the new scheme without guessing which equal-version build came first. Version information on a damaged installation still guards against rollback. A failed or interrupted overlay must not qualify as healthy solely because an old or new manifest exists.

## Private settings and application boundaries

**Decision** — Keep all writes within the current packaging and workstation setup boundaries.

**Rationale** — The default immutable root is `%LOCALAPPDATA%\Programs\EngineeringMemory`. The private config and data roots are under `%LOCALAPPDATA%\EngineeringMemory`; custom paths and Docker volumes belong to the existing profile. The wizard already routes settings reads/saves and MCP scan/apply through the installed helper, with stale checks and per-target consent. Reusing those actions preserves blank-key and deferred-step behavior. Stage maintenance choices until confirmation so cancelling the wizard cannot inadvertently commit settings.
