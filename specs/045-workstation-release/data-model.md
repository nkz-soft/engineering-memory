# Release and Acceptance Records

| Record | Fields and constraints |
| --- | --- |
| Release identity | Version `0.0.1`, tag `v0.0.1`, approved commit SHA. Tag version equals project and package metadata. |
| Candidate asset | Platform, filename, SHA-256 and corresponding checksum sidecar. One Windows binary, one Ubuntu package and one Ubuntu launcher. |
| Workstation acceptance | OS and architecture, candidate commit and tag, accepted digests, Docker and Compose versions, commands, readiness/import/reinstall/retry results and sanitized diagnostics. Two passing supported platforms are required to publish. |
| Workstation profile | Existing per-user environment files, archive and SQLite state. Stack data stays in the existing Docker volume. Reinstall preserves their ownership and contents. |

The release adds no application schema. Configuration and evidence remain separate from the bundled payload.
