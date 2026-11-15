# Data Model

| Entity | Fields | Rules |
| --- | --- | --- |
| Setup profile | User scope, provider model identifier, optional API base, provider credential, proxy key, two ports, archive path, SQLite path | Distinct valid ports and absolute persistent paths outside the payload. The two files describe the same loopback endpoints and proxy key. Credentials are opaque to prompts after entry. |
| Client target | Client kind, detected executable if available, active user profile, registration state | A matching target is the installed executable plus exactly the `serve` argument. Track absent, matching, conflicting, unavailable and failed states without recording third-party config content in logs. |
| History candidate | Source kind, local path, discovery origin, user selection | Deduplicate canonical paths within a source kind. File selection is distinct from stable conversation identity, which remains the importer's responsibility. |
| Source result | Candidate reference and imported, unchanged/skipped and failed counts, or a safe source-level error category | Unselected sources are tracked separately. A source-level failure can have unknown conversation counts. |

The wizard moves from profile confirmation to Docker readiness and provisioning, then registration and optional import. Registration failures permit import once provisioned. An aborted or interrupted run can be restarted from persisted settings, current registrations and ordinary importer state.
