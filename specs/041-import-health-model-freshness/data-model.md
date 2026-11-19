# Status Data Model

## Source health

Keyed by the canonical source enum. Store the latest completed attempt timestamp, outcome, closed error category set, deferred count and last confirmed import timestamp. Attempt outcome is healthy, waiting, partial or failed. An absent attempt projects as unobserved. Waiting means a successful scan found deferred work and committed no new conversation. A successful import with deferred work preserves both facts.

Update the attempt tuple atomically in observed completion order. Order competing outcomes by completion timestamp with database commit order as the tie-breaker. Update the separate success timestamp using the maximum confirmed import timestamp. A dry run performs neither update. A failure to persist status is surfaced through fixed operational handling and cannot make the page claim a successful write.

## Project import evidence

Keyed by a validated classified project slug. Keep the maximum pre-retain start and the maximum acknowledged completion time observed across confirmed imports. Commit them atomically with the successful conversation record and source success timestamp. Exclude unclassified imports, failed imports, unchanged skips and observations with a backwards clock. A crash preserves only committed observations. The two timestamps bound possible ordering and do not identify individual imports.

Use a transactional additive migration from SQLite schema v1 and v2. The read-only path accepts both old schemas and returns absent health data. Keep the existing strict schema checks for each version. Use atomic upserts and no backfill from mutable conversation records. An unreadable database returns unavailable rather than empty.

## Model health

Per selected project and model kind, return refresh state ready, missing, pending, failed or unavailable, last completed refresh time, last failed refresh time and freshness stale, unknown or current. A prior usable refresh remains visible alongside later failure metadata. Backend model text, support references and refresh operation identifiers never enter the status projection. Use UTC timestamps for interchange and only compare times when the backend time semantics make the ordering meaningful. See [freshness rules](research.md#model-metadata-uses-the-existing-gateway).
