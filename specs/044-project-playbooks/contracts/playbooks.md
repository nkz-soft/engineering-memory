# Project Playbooks Contracts

## Operator CLI

All commands use the existing local archive-root configuration.

- `engineering-memory playbooks stage --project PROJECT --id ID --file FILE` reads a bounded UTF-8 JSON object with exactly `title`, `steps` and `examples` (ordered document IDs). Enforce a 512 KiB input cap. Resolve and validate same-project examples and output the new revision token. An invalid replacement leaves any existing draft intact.
- `engineering-memory playbooks review --project PROJECT --id ID` shows the revision token, sanitized title, numbered steps and source references for the pending draft.
- `engineering-memory playbooks approve --project PROJECT --id ID --revision TOKEN` publishes the indicated revision and outputs its approved version. A replacement draft, changed or missing evidence, and invalid input produce a nonzero exit and a scoped recovery message. Retrying an already approved revision returns its version.

## MCP and explorer

| MCP tool | Explorer read route | Inputs |
| --- | --- | --- |
| `list_project_playbooks` | `POST /api/playbooks/list` | `project`, optional `after_id`, optional `limit` (1–100, default 20) |
| `get_project_playbook` | `POST /api/playbooks/get` | `project`, `id`, optional positive integer `version` |

List returns `items` with `id`, `title` and latest approved `version`, plus `next_after_id` or null. Get returns `project`, `id`, `title`, `version`, `latest_version`, `approved_at`, ordered `steps` and ordered `examples`. Each example has `document_id`, `project`, `source_timestamp` and `snapshot`. No published match returns a generic not-found result. Absent storage returns an empty list and not-found detail. Storage failure returns a generic unavailable error. Use existing strict validation and transport error envelopes. HTTP routes inherit the existing loopback, authentication, Host/Origin and no-store controls.

Extend the existing MCP `get_conversation` request with the optional pair `project` and `snapshot`; use the existing guarded browser request behavior. If the pair is supplied, changed, missing or mismatched evidence yields the existing guarded error and no transcript content. Callers that omit both fields retain the existing paginated response.

The Playbooks panel uses the active exact project, offers approved version selection and opens examples through the guarded viewer. Invalidate outstanding requests when project or selection changes. Render text literally. MCP tool descriptions mark procedure and evidence text as untrusted data. All MCP and browser operations are read-only.
