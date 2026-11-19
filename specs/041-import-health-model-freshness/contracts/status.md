# Explorer Status Contract

`POST /api/status` accepts an object with an optional validated `project` slug. An empty object requests source health only. Reuse the protected dispatch with exact loopback Host and Origin, bearer authentication, bounded JSON, fixed error codes and no-store headers.

A successful response contains only these fields.

| Field | Allowed values |
| --- | --- |
| `source_status` | `available`, `unavailable` |
| `sources` | When available, one row each for ChatGPT, Claude Chat, Claude Code and Codex using canonical source identifiers. When unavailable, an empty list. |
| `models` | One row per architecture, stack and decisions model when a project is selected. An empty list for source-only reads. |

Source rows contain `source`, `outcome` (healthy, waiting, partial, failed, unobserved), `last_attempt_at`, `last_success_at`, `deferred_count` and `error_categories`. Timestamps are UTC or null. Categories are a deduplicated set from the fixed pipeline stages and fixed runtime categories configuration, state, memory, internal and unknown. Unknown stored categories map to unknown. Unobserved status carries no active error.

Model rows contain `kind`, `refresh_state`, `last_refreshed_at`, `last_refresh_failed_at` and `freshness` as defined in the [data model](../data-model.md). A model lookup failure yields an unavailable row with unknown freshness unless independently usable metadata was already obtained for that row. It does not discard source health.

The request starts no import, refresh or background action. The browser displays null times as unavailable or not yet recorded as appropriate, uses fixed accessible labels, and clears rendered data on lock. The browser handles scope changes without displaying a prior project's result.
