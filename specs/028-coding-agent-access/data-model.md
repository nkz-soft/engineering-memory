# Data model: Coding-agent access

No production schema or source-model change is planned.

## Consumer registration

Fields: client name/version, server name, absolute executable, argument vector,
forwarded environment variable names and configuration scope. Both registrations
resolve the same backend bank and normalized archive. Tokens are never evidence fields.
Lifecycle: documented -> registered -> discovered -> tool-invoked. Registration is not
successful acceptance until the client actually retrieves the expected evidence.

## Acceptance conversations

Decision: native ChatGPT identity, original timestamp, synthetic project and decision.
Refinement: native Claude Code session identity, original timestamp, same project and
new refinement. A competing decision uses a different project. Existing normalization,
sanitization, provenance and tag contracts apply without modification.

Lifecycle: staged complete snapshot -> dry-run checked -> archived/imported -> retrievable.
A live refinement is absent before import. Unchanged reimport is skipped; changed content
retains its native document identity. No explicit foreign-key relationship is added.

## Verification record

Fields: date, repository revision, client/runtime versions, safe setup and import commands,
discovered tools, query/filter, returned document identity/provenance/time, normalized
context outcome, negative-filter and reimport outcomes, journey status and blocker reason.
Statuses: unverified, blocked, failed, passed. A required skip cannot become passed.
Evidence uses synthetic content only and separates actual clients from SDK/backend checks.
