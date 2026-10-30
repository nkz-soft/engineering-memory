# Data Model: Bank Provisioning

No new database tables, archive records or import-state schema.

| Entity | Fields | Validation / ownership |
|---|---|---|
| Provisioning target | existing base URL, bank id, optional token | Existing HindsightSettings; token stays secret; bank path encoded; default engineering-global |
| Retain mission | complete version-controlled text | Exact Architecture §12 priority and exclusion sections; nonempty; preserved during JSON serialization |
| Verified result | success status | Returned only after exact mission read-back; CLI exits zero |
| Failure | safe category | Configuration, unavailable/permission, invalid response, mismatch; no response bodies or raw exceptions |

State transitions: absent → configuration write (and dedicated creation only if required by the pin) → verify → ready. Existing old mission → update only retain mission → verify → ready. Existing matching mission → verify/apply safely → ready. Any interrupted step leaves rerunnable state; no rollback deletes the bank. No persistent local ready flag is authoritative.
