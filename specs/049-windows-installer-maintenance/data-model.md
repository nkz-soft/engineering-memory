# Data Model: Windows Installer Maintenance

## Build manifest

| Field | Meaning and validation |
| --- | --- |
| Schema version | Known format only. Missing or unsupported schemas cannot establish health. |
| Release version | Valid numeric release version supported by the Windows package. It must agree with the installed registration for a healthy result. |
| Build identity | Canonical SHA-256 of the normalized manifest inputs and installer recipe fingerprint. Equality only. |
| Recipe fingerprint | Hash of the installer recipe used for the build. |
| Payload entries | Sorted unique relative paths and SHA-256 content digests. Reject ambiguous case matches, invalid or escaping paths, reparse points that redirect checks, duplicate entries and malformed digests. Require the launcher and its bundled runtime in the inventory. |

The incoming package carries the manifest and its identity. The installed manifest describes app files only and never records config values, history, client paths or credentials. A missing or mismatched listed file fails health verification. Normal installer-generated metadata is outside the payload inventory.

## Installation observation

- Effective current-user application path and whether its existing registration and contents agree.
- Installed version evidence and any conflicting or invalid evidence.
- Health status, verified identity when present, and a safe diagnostic reason.
- The incoming package is evaluated against this observation once for display and again at the relevant write or helper boundary.

## Transitions

- Fresh → installed incoming build after verified copy.
- Healthy identical → unchanged installation after exit, no-op or configuration.
- Healthy older → installed incoming build after update.
- Healthy same version with different identity → installed incoming build after confirmed replacement.
- Incomplete with adequate version evidence → installed incoming build after confirmed, verified repair.
- Blocked, cancelled before commit, or silent consent-required state → unchanged.
- Failed payload operation → re-observe actual files and registration on retry. Advance the recorded ready state only after the incoming payload verifies.
