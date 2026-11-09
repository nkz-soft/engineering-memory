# Acquisition data model

| Entity | Fields and constraints |
|---|---|
| Candidate | Input path, mode (`manual` or `watcher`), non-secret origin label. The path is transient and never emitted. A watcher observation stores local file identity, size, modification time and first-observed time privately for readiness checks. |
| Archived export | `source=chatgpt`, SHA-256 digest and exact original bytes. Place ZIPs in a dedicated archive namespace such as `exports/chatgpt/<sha256>.zip`, outside conversation enumeration. Derive the locator from source and digest. |
| Acquisition | Unique `(source, digest)`, mode, non-secret origin label, `acquired_at` in UTC, optional `produced_at` in UTC, `production_evidence` (`source_timestamp`, `zip_member_estimate` or `unknown`), and nullable `ingested_at` in UTC. Unknown evidence requires null `produced_at`. Preserve the original acquisition origin on duplicates. |

Publish before recording. A null `ingested_at` denotes pending import, including partial, failed or interrupted runs. Only a successful report sets it. Use a deterministic digest tie-break when reading the most recently completed acquisition. Keep previous completed acquisitions and conversation rows intact on pre-import failure. No raw ZIP bytes belong in SQLite.
