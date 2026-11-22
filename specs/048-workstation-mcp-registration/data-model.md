# Data Model: Workstation MCP Registration

| Entity | Fields and invariants |
| --- | --- |
| Client installation | Stable product ID, display name, trusted install evidence, current platform and optional verified profile file. A client may be discovered with a profile resolution diagnostic |
| Profile target | Canonical effective file, TOML or JSON format, member client IDs, opaque scan identity. One operation for each unique profile regardless of member count |
| Inspection | Missing, matching, conflicting or blocked; in-memory snapshot of source/path identity, with an opaque digest or token binding consent to it. Never expose raw configuration or include it in installer state |
| Selection | Explicit opt-in for one profile plus a separate replacement grant for its specific conflict and snapshot. Absent or stale authorization causes no edit |
| Result | Persisted state and local probe state per target, projected to member clients. An operator's fresh-session check is recorded independently |

Discovery and inspection are read-only. An opted-in missing entry proceeds to an atomic add, a match goes to read-back, and a conflict requires replacement consent before revalidation and write. A changed snapshot, misdirected target or failed write ends that attempt. A verified read-back is the only state eligible for the local probe. Re-running setup performs discovery and inspection again.
