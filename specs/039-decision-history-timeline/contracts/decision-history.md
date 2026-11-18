# Explorer Decision History Contract

## Browser request

`POST /api/deep-recall` with the existing exact Host, same-origin Origin and bearer credential, and a JSON body:

```json
{"project":"sample-project","query":"cache policy","mode":"decision_history"}
```

`mode` is a browser request field. Omitting it uses ordinary Deep Recall with the existing response shape. Other values fail with 400. Project and query follow the existing Deep Recall limits and validation, including rejection of blank queries and unclassified scope. The route uses existing response headers, body limit and error mapping, including 503 with `synthesis_unconfigured`. Decision history calls `MemoryAccess.decision_history(project=..., query=...)`. The stdio MCP schema is unchanged.

## Decision history response

| Field | Shape |
| --- | --- |
| `project`, `topic` | Validated slug and trimmed query |
| `status` | `completed`, `partial`, `insufficient_evidence` or `verification_failed` |
| `events` | Event objects described below |
| `conflicts` | Objects with `summary` and `accounts`; each account has `text` and anchor array `citations` |
| `coverage`, `uncertainty` | Existing Deep Recall coverage object and sorted reason codes, with additional chronology and conflict reasons |

An event has `kind`, `version`, nullable `prior_version`, nullable `reason`, `action` as a message anchor, `context` as an anchor array, nullable ISO timestamp `occurred_at`, `chronology` and boolean `ordering_uncertain`. Dated events sort oldest first by normalized instant, then by source identity and position, then event kind. Unknown and disputed events follow with null `occurred_at` under a visibly undated or disputed heading. The original anchor timestamp stays available to the message viewer. The service returns `partial` when verified events or conflicts coexist with limits, evidence gaps, ordering ambiguity or unresolved conflict. Conflict-only evidence is a valid partial result. Empty and failed outcomes contain no events or conflicts.

The synthesis draft allows up to 12 events and 6 conflicts with 2–4 accounts each. Text fields are bounded to 600 characters and each event or account has 1–4 selectors total, including the primary action selector for an event. Supersession includes an action selector and a source phrase naming the previous version. The action citation can provide that phrase, and a contextual citation can supply it when needed. A displayed reason must use a phrase from the action or a contextual citation. The existing transport byte and timeout budgets apply. Malformed or unverifiable output takes the fixed verification-failure path. The selector-to-anchor map is server-side.

## Browser interaction

A **Decision history** action uses the current project and query. An ordered list uses readable event labels and exposes versions, reasons and dates where supported. Unknown times, disputed times and ties have visible text. An **Unresolved conflicts** section gives each account its own evidence controls. Activating the event source or a citation opens the existing conversation panel at the verified message offset and highlights the evidence. Missing or changed sources use the existing unavailable-source state. Lock, a new lookup and a project change clear panel contents and abort or ignore stale requests. Render every result with inert text.
