# Engineering Memory — Architecture

Status: architecture fixed, implementation not started. The technology stack is
Python, decided in ADR-004 (see §20).

## 1. Purpose

Build a single long-term engineering memory that aggregates the user's
accumulated interaction history with AI systems, so that an agent can retrieve
relevant context from past conversations, technical decisions, incident
investigations and development history.

**Primary goal: give Hermes access to the user's ChatGPT and Claude history —
both plain chats and coding-agent sessions.**

Everything else — Claude Code and Codex reading the same memory, mental models,
evaluation — follows from that, and is sequenced after it.

hermes-memory is the store of that history, not only its importer. Hermes and
every other consumer reach it through the MCP server hermes-memory exposes, and
never through Hindsight directly (ADR-008).

Hindsight is the memory engine. We do not build our own RAG, and we do not add a
vector database, a search engine or a custom knowledge graph. Hindsight owns
fact extraction, entity resolution, the knowledge graph, temporal relationships,
retrieval, reranking, consolidation, observations, mental models, and the
`retain` / `recall` / `reflect` operations.

## 2. Sources and consumers

Sources of history:

* ChatGPT export — **the only source in the MVP**;
* Claude chats;
* Claude Code sessions;
* Codex sessions;
* Hermes conversations.

Every source beyond ChatGPT is added as a separate piece of work with its own
architectural decision record. Nothing in this document assumes them.

Consumers of memory:

* Hermes — the primary consumer;
* Claude Code;
* Codex;
* other coding agents later.

Every consumer reaches memory through the memory access surface (§16), and none
is configured against Hindsight itself — not for reads, and not for writes.

## 3. Principles

### 3.1. Hindsight is derived memory, not the source of truth

Original exports are stored independently of Hindsight.

```text
Raw Archive  ──►  Importer  ──►  Hindsight
```

`retain()` extracts structured memories from the input; the original text must
not live only inside Hindsight. Keeping an independent archive lets us change
the extraction policy, upgrade Hindsight, change the retain mission, fix the
parser, apply new redaction rules, and re-run ingestion — without going back to
the original services for another export.

### 3.2. Memory is scoped by tags, not by consumer

Do not create per-agent memory (`claude-memory`, `codex-memory`,
`chatgpt-memory`). The originating system is recorded as metadata on the
content, never as a separate store. Project separation is expressed through
tags — see §5 and ADR-002.

### 3.3. Provenance is mandatory

Every imported conversation must make it possible to determine its source,
original ID, original time, project, repository (when known), and the version of
the importer that produced it.

```json
{
  "source": "chatgpt",
  "source_id": "conversation-id",
  "project": "miratorg",
  "repository": "",
  "title": "Wolverine Saga Error Handling",
  "imported_at": "2026-09-12T10:00:00Z",
  "importer_version": "1"
}
```

Hindsight stores metadata alongside memory units and returns it on retrieval.

### 3.4. Consumers depend on hermes-memory, not on the engine

A consumer is configured against hermes-memory's MCP server and sees its tools,
never Hindsight's endpoints, banks or vocabulary. The memory engine is then
replaceable for consumers as well as for ingestion: swapping it changes one
implementation behind `memory/interface`, and no agent is reconfigured. The
same surface is what lets a consumer read a whole archived conversation behind a
recalled fact, which extracted memory alone cannot give back (ADR-008).

## 4. Overall architecture

```text
                    ┌─────────────────────┐
                    │    DATA SOURCES     │
                    │                     │
                    │ ChatGPT export      │  ← MVP
                    │ Claude chats        │
                    │ Claude Code         │  ← later, separate ADRs
                    │ Codex               │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Import Service    │
                    │                     │
                    │ Parse               │
                    │ Normalize           │
                    │ Sanitize            │
                    │ Classify            │
                    │ Enrich metadata     │
                    └──────────┬──────────┘
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
           ┌─────────────┐          ┌──────────────┐
           │ Raw Archive │          │  Hindsight   │
           │             │          │              │
           │ originals   │          │ facts        │
           │ normalized  │          │ entities     │
           └──────┬──────┘          │ graph        │
                  │                 │ observations │
                  │                 └──────┬───────┘
                  │ normalized only        │ recall / reflect
                  │                        │ (memory/interface)
                  └────────────┬───────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Memory access       │
                    │ surface (MCP)       │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
              Hermes      Claude Code      Codex
            (primary)       (later)       (later)
```

A self-hosted Hindsight instance is deployed separately, and only hermes-memory
talks to it. Consumers reach memory through the access surface (§16, ADR-008).
Neither the Hindsight instance embedded in Hermes nor Hermes's native Hindsight
memory provider is used: memory must be reachable by more than one consumer, and
a consumer that wrote to Hindsight directly would create memory with no original
in the raw archive (§3.1).

## 5. Memory bank strategy

**One shared bank: `engineering-global`.** Project separation is expressed
through `project:` tags, which consumers use to filter at recall time.

This is a deliberate departure from the per-repository convention used by the
official coding-agents integration, and is recorded as ADR-002.

## 6. Tags

A strict, stable convention — tags are the only scoping mechanism, so their
naming is part of the architecture:

```text
source:chatgpt          source:claude-chat
source:claude-code      source:codex
source:hermes

project:<slug>          project:unknown

type:conversation       type:coding-session
type:decision           type:troubleshooting

user:<user-id>
```

Hindsight supports tag filtering on `recall` and `reflect`, with match modes
(any / all / strict / exact). Hermes exposes the same filtering to its provider
configuration.

## 7. Ingestion pipeline

Logical stages, each independently testable:

```text
Source
  │  parse       — read the export, reconstruct conversation structure
  ▼
Normalize       — map to a source-independent conversation model
  │
  ▼
Sanitize        — redact secrets, preserve surrounding context
  │
  ▼
Classify        — determine the project
  │
  ▼
Enrich          — attach provenance metadata and tags
  │
  ├──────────────► Raw Archive   (originals + normalized form)
  │
  ▼
Hindsight retain
```

The pipeline is composable, and runs conversation by conversation.

A conversation is sent as **one logical document**, not message by message, so
that extraction sees the whole context.

## 8. Boundaries

Every boundary is an interface, so that any single part can be replaced without
disturbing the rest — in particular Hindsight itself (ADR-001, exit strategy):

| Boundary | Responsibility |
|---|---|
| Conversation source | Read one source format, yield normalized conversations |
| Secret sanitizer | Redact secrets, report what was redacted |
| Project classifier | Determine the project for a conversation |
| Raw archive | Persist originals and normalized forms |
| Memory store | `retain` / `recall` — the only component aware of Hindsight |
| Import state | Track what has already been imported |
| Memory access surface | Serve memory and archived conversations to consumers over MCP |

Neither the domain model, the pipeline nor the access surface references
Hindsight. Only the memory store implementation does. The access surface reads
through `memory/interface` and the raw archive's interface, exactly as ingestion
writes through them.

## 9. Hindsight contract

Verified against the current Hindsight documentation. Recorded here because the
architecture depends on these semantics, not as an implementation detail.

| Operation | Endpoint |
|---|---|
| Retain | `POST /v1/default/banks/{bank_id}/retain` with `{ "items": [ … ] }` |
| Recall | `POST /v1/default/banks/{bank_id}/recall` |
| Bank config | `PATCH /v1/default/banks/{bank_id}/config` |

Per-item fields that carry our architecture: `content`, `document_id`,
`timestamp`, `context`, `metadata`, `tags`, `document_tags`, `update_mode`.
Request-level: `async`, `operation_id`.

Semantics we rely on:

* **Banks are created by writes, not reads.** A read against a bank that has
  never been written returns `404`. A bank must therefore be provisioned before
  first use — and the config call itself counts as a write.
* **`document_id` gives idempotent upsert.** With the default
  `update_mode: "replace"`, re-importing the same logical document replaces the
  previous version instead of creating duplicates.
* **`operation_id` is a separate retry idempotency key**, so a retry after a
  timeout does not pay for extraction twice.
* **`update_mode: "append"`** allows a single logical document to be delivered
  as several items — the mechanism for conversations too large to send at once.
* **`timestamp` drives temporal grounding**, and is per item.

## 10. Document identity

`document_id` is mandatory and stable across runs:

```text
chatgpt:{conversation-id}
claude-chat:{conversation-id}
claude-code:{session-id}
codex:{session-id}
hermes:{session-id}
```

A freshly generated identifier per import run is never acceptable — it is what
turns a re-import into duplicated memory.

## 11. Timestamps

Send the conversation's real timestamp. The import date must never be used as
the conversation date, because temporal retrieval depends on it: questions like
"what did we use before", "when did we move to X", "how did the decision change"
degrade without it.

## 12. Retain mission

Extraction is steered toward durable engineering knowledge:

```text
Prioritize:
  architecture decisions and rationale; technology choices; implementation
  decisions; debugging investigations; root causes; successful fixes;
  unsuccessful approaches and why they failed; infrastructure configuration;
  deployment procedures; API contracts; data model decisions; migrations and
  version changes; coding conventions; project constraints; security decisions;
  operational lessons.

Do not prioritize:
  greetings; conversational filler; temporary wording; repetitive status
  messages; credentials or secrets.
```

The mission is **bank-level configuration**, not a property of an individual
retain call — see ADR-003.

## 13. Secret sanitization

Historical imports are sanitized before reaching Hindsight.

Minimum categories: API keys, bearer tokens, JWTs, GitHub and GitLab PATs,
Anthropic and OpenAI keys, AWS access keys, private keys, passwords, connection
strings, `.env` values, Kubernetes secrets.

Values are replaced with `[REDACTED]` while the surrounding context is
preserved, because the context is often the knowledge worth keeping:

```text
Bad:   drop the entire tool output
Good:  GitLab request using token [REDACTED] returned HTTP 401 Unauthorized
```

## 14. Raw archive

Originals and normalized forms are stored separately from Hindsight, behind an
interface, so the backing store can change without touching ingestion. Local
storage in the MVP; object storage is a later option.

## 15. Project detection

1. **Explicit metadata** — use the repository or working directory when the
   source carries it.
2. **Deterministic rules** — match known repository names, paths, project names
   and aliases.
3. **Model-based classification** — out of scope; an extension point is left for
   it.

ChatGPT exports carry no repository or working directory, so level 1 does not
apply to the MVP source and detection rests on alias matching. A substantial
share of conversations will not resolve to a project. They are still imported,
tagged `project:unknown`, and remain retrievable — which is possible precisely
because there is one shared bank (ADR-002).

## 16. Retrieval

`recall` for ordinary lookups: it combines semantic, keyword, graph and temporal
retrieval, and must return facts regardless of which system they originated in.

`reflect` for questions that require synthesizing many memories — how an
approach evolved, what the overall shape of a decision is. Not for every query;
it is slower and reasons over accumulated memory rather than fetching it.

### 16.1. Memory access surface

Consumers retrieve through an MCP server that hermes-memory exposes, not through
Hindsight (ADR-008). It is a module of the monolith, `access`, and depends only
on `memory/interface`, the raw archive and the import state.

| Tool | Backed by | Returns |
|---|---|---|
| `search_memory` | `recall` | Matching memories with their provenance and `document_id`; filters for project, source and time are expressed as tags (§6) |
| `get_conversation` | raw archive | The normalized form of one conversation by `document_id`, in pages of messages |
| `reflect` | `reflect` | A synthesized answer over accumulated memory |
| `list_conversations` | import state | Conversations by project, source and time, with titles and document ids |

`search_memory` and `get_conversation` are the first two; `reflect` and
`list_conversations` arrive with the features that need them, as does any method
they require behind the boundaries.

`get_conversation` serves the normalized form only. The original is never
served, because it is the one form that has not been sanitized (§13, §19).

The surface is read-only. Memory is written by importers alone, so everything a
consumer can find has an original in the raw archive (§3.1). A consumer's own
conversations — Hermes's included — enter memory as a history source of their
own (§2), not through a write tool.

## 17. Idempotency and import state

Re-running an import must be safe and must not create duplicate documents.

Two independent layers:

* **Hindsight side** — stable `document_id` guarantees upsert semantics.
* **Importer side** — a local record of what was imported (source id, content
  hash, document id, time, status). A conversation whose source id and hash are
  unchanged is skipped before any call is made, which avoids paying for
  extraction again.

The content hash is computed over a canonical representation of the normalized
conversation.

ADR-006 settles what that representation covers, and what a re-run does with a
conversation that grew, disappeared or was renamed between two exports.

## 18. Error handling, retry and observability

Import proceeds conversation by conversation; one failure must not abort the
run. The outcome is reported as imported / skipped / failed, and each failure is
recorded with its source id, error and time.

Retry transient failures only — 429, 502, 503, 504, connection resets, timeouts
— with exponential backoff and jitter, reusing the same idempotency key. Never
retry 400, 401, 403 or invalid input.

Structured logs per ingestion operation: source, source id, project, bank,
document id, start time, duration, status, error. Conversation contents are not
logged by default. Credentials, tokens and raw authorization headers are never
logged.

## 19. Security

1. The raw archive stays local.
2. Secrets are redacted before Hindsight.
3. A self-hosted Hindsight instance is used; data is not sent to a hosted one.
4. The LLM provider used for extraction is configurable, and reached through an
   OpenAI-compatible endpoint — an existing LiteLLM proxy in this setup, so the
   actual model is proxy configuration rather than anything hardcoded here.
5. Credentials come from environment variables or a secret store, never from
   configuration files in the repository.
6. The access surface runs over the stdio transport, as a process the consumer
   starts on the same machine: it opens no port and needs no credential of its
   own. It serves sanitized content only, and logs what it serves under the
   same rules as §18.

## 20. Technology stack

The stack is decided in ADR-004: Python 3.13, with a modular monolith calling an
external Hindsight instance. The decisions this section previously deferred are
settled there — language and runtime, import-state storage, raw archive layout,
configuration, the command-line surface and the testing framework.

None of it changes anything above: the stack was chosen to fit the architecture,
not the other way round.

Still open, and deliberately so, are the details that only implementation can
settle — the on-disk layout of the raw archive, the schema of the import-state
store, and the exact command surface. They are constrained by ADR-004 rather
than free choices, and are fixed by the first specification that needs them.

## 21. Out of scope for the MVP

Custom vector database, embeddings, reranker, knowledge graph or RAG pipeline;
web frontend; multi-user authorization; distributed ingestion; message queues;
background workers; model-based project classification; cross-bank
synchronization; Confluence, Jira and GitLab importers; mental model management;
write tools on the access surface; an access surface reachable over the network.

## 22. Phases

### Phase 1 — MVP: ChatGPT history reachable from Hermes

1. Hindsight runs locally through a documented setup, with extraction routed
   through the LiteLLM proxy.
2. The bank is provisioned and its retain mission configured.
3. ChatGPT exports are parsed into the normalized conversation model.
4. Secret sanitization works.
5. Deterministic project classification works.
6. Originals and normalized forms are archived.
7. Conversations are retained with stable document ids, original timestamps,
   provenance metadata and tags.
8. Re-importing creates no duplicates.
9. A dry run reports what would happen without contacting Hindsight.
10. Parser and sanitizer are covered by tests.
11. An end-to-end test imports a conversation and retrieves a fact from it.
12. The access surface serves `search_memory` and `get_conversation` (§16.1).
13. **Hermes, connected to the access surface over MCP, finds that fact and
    opens the conversation it came from.**

Item 13 is what makes the phase meaningful; the rest is the means.

### Phase 2 — coding agents

Claude Code and Codex connect to the same access surface. Their sessions enter
memory through importers of their own, including tool calls, so that the chain
command → error → investigation → solution is preserved and every session has
an original in the raw archive. Acceptance: a decision discussed in ChatGPT and
imported is found by Claude Code; a refinement made in Claude Code, once its
session is imported, is visible to Codex.

### Phase 3 — synthesis

Mental models for project architecture, current stack and architecture
decisions. `reflect` verified. An evaluation dataset of at least 30 questions
with expected topics, so that memory quality can be compared objectively after
changes to the retain mission, the extractor model, the Hindsight version or the
bank strategy.

## 23. Decision records

### ADR-001 — Hindsight as the memory engine

**Decision.** Use Hindsight as the primary long-term agent memory engine.

**Rationale.** It already provides fact extraction, entity resolution, a
knowledge graph, temporal memory, retrieval, reranking, consolidation,
observations, mental models, MCP, coding-agent integrations and a native Hermes
provider. Building our own RAG first would duplicate all of it.

**Consequences.** Less code, faster MVP, one memory API, memory shared across
agents, temporal reasoning — against a dependency on Hindsight's data model, a
retrieval pipeline that is partly a black box, and the obligation to maintain a
separate raw archive.

**Exit strategy.** The raw archive and the normalized conversation model are
independent of Hindsight, so the backend can be replaced later without
re-exporting anything from the original services.

*Revisited by ADR-008:* consumers no longer use the native Hermes provider or the
coding-agent integrations; they reach memory through hermes-memory's own MCP
server, which extends the exit strategy from ingestion to consumers.

### ADR-002 — One shared bank, projects separated by tags

**Decision.** Use a single bank, `engineering-global`, with `project:` tags for
scoping, instead of one bank per repository.

**Rationale.** The Hermes memory provider reads exactly one bank and has no
multi-bank query capability. With per-repository banks, Hermes would see one
project rather than the whole history — which contradicts the primary goal in
§1. Tag filtering is supported by both Hermes and the coding-agent integration,
so scoping is preserved without splitting storage. It also gives conversations
that resolve to no project somewhere to live (§15).

**Consequences.** Retrieval has more to sift through as the corpus grows, and we
depart from the official per-repository convention. Coding agents must be
pointed at this bank explicitly rather than using their default. If retrieval
quality degrades, the alternative is per-project banks plus a duplicate write
into a global bank — which costs extraction twice and requires cross-bank
synchronization that is currently out of scope. Because the bank is a
configuration value, that change would not alter the importer.

*Revisited by ADR-008:* the single-bank limit of the Hermes provider no longer
binds, because Hermes no longer uses that provider. The decision stands on its
remaining grounds — one place for conversations that resolve to no project, and
extraction paid once — and splitting banks later would change only the memory
store implementation, not any consumer.

### ADR-003 — Retain mission is bank configuration

**Decision.** Configure the retain mission on the bank, not per retain call.

**Rationale.** Hindsight exposes the mission through the bank config API and a
server-level environment variable; it is not a per-item field.

**Consequences.** Provisioning becomes an explicit, separate step from
ingestion: the bank must be created and configured before the first import, and
changing the mission is an operation on the bank that affects everything
extracted afterwards. Since banks are created by writes only, the provisioning
call is also what brings the bank into existence.

### ADR-004 — Python as the implementation stack

**Decision.** Implement the system in Python 3.13, as a modular monolith that
calls an external Hindsight instance over HTTP/MCP.

The core is `uv` for dependencies, Typer for the command line, Pydantic v2 for
the domain model and contracts, httpx for HTTP, SQLAlchemy 2 over SQLite for
import state in the MVP and PostgreSQL in production, local storage for the raw
archive in the MVP and S3/MinIO in production, Tenacity for retry, structlog and
OpenTelemetry for observability, pytest with testcontainers for tests, FastAPI
if and when an HTTP surface is needed, and Docker for packaging. The full table
lives in the project constitution, which is where compliance is checked; this
record holds the reasoning.

Module layout mirrors the boundaries of §8 — `ingestion`, `normalization`,
`sanitization`, `classification`, `archive`, `memory/{interface,hindsight}`,
`evaluation`, `observability`, plus `cli` and `api`. Only `memory/hindsight`
knows about Hindsight.

**Rationale.** This is an AI/agent/RAG project, and that ecosystem — memory
engines, rerankers, embedding models, evaluation tooling — appears in Python
first, with reference implementations to match. The work ahead is largely
experimental: different ingestion strategies, classifiers, sanitizers, retrieval
approaches and evaluation sets, each cheap to try and often discarded. Python
lowers the cost of that loop, and it is the shortest path both to Hindsight and
to any replacement for it, which is what makes the exit strategy of ADR-001
real rather than theoretical.

The priority order behind the choice is explicit: time-to-experiment, then
ecosystem access, then replaceability of components, then developer
productivity, then raw throughput. Maximum static typing and enterprise-platform
consistency are not the target — .NET/C#, the original draft's candidate, wins
on those and loses on the ones that matter here.

**Consequences.** Less type safety at compile time, which Principle III of the
constitution compensates for by requiring tests first; Pydantic carries contract
validation at the boundaries instead. Runtime throughput is lower than a
compiled stack would give, which is acceptable because ingestion is bounded by
LLM extraction and network calls, not by local compute. Two storage targets
(SQLite/local now, PostgreSQL/object storage later) must sit behind the same
interfaces from the start, or the migration becomes a rewrite.

If the project later grows into a high-load multi-tenant platform, individual
components can move to Go, .NET or Rust. Ingestion, memory and evaluation stay
in Python: they are where experimentation continues.

### ADR-005 — Issues are taken into work locally, gated after planning

**Decision.** A feature request filed as a GitHub issue is carried to a pull
request by one local command, `/issue-to-pr <number>`, which runs Spec Kit for
the specification and plan, stops for a human, and only then implements and
opens the pull request. The configuration is documented in
[`docs/workflow/issue-to-pr.md`](docs/workflow/issue-to-pr.md).

**Rationale.** The alternative was a GitHub Actions workflow triggered by a
label or a mention, which would run unattended. It was rejected on three counts:
it needs an API key in repository secrets for a public repository whose subject
matter is private engineering history; the Spec Kit and Superpowers skills that
make the work compliant would have to be installed into a runner on every run;
and the interactive steps this project depends on — `/speckit-clarify`, the
constitution compliance statement in every plan — have no one to answer them
there.

The gate sits after planning rather than before implementation's end because
that is where correction is cheap. A specification and a plan take minutes to
redirect; an implementation built on a misread issue costs a review cycle and a
rewrite. Placing it anywhere else would either surrender the correction (no
gate) or spend a human on questions an assumption could have settled (a gate per
step).

**Consequences.** Nothing progresses while the developer's machine is off, and
an issue cannot be picked up by filing it alone — someone runs the command. In
exchange there are no secrets to hold, no Actions minutes, and the full local
skill set applies. The loop keeps no state of its own: the phase is inferred
from the git worktree and the committed plan, so a resumed session reads the
world rather than a memory of it, at the cost of the gate having to leave its
record as an issue comment. Work runs in a worktree of its own, so the primary
checkout stays usable and two issues can proceed at once, against one dependency
environment per worktree. That worktree sits inside the checkout, at
`.claude/worktrees/<number>` and excluded by `.gitignore`, rather than beside
it: a path outside the working directory costs a permission prompt on every file
the run touches, which would leave the loop stopping far more often than at its
one intended gate.

### ADR-006 — History is re-exported periodically, imported incrementally

**Decision.** After the first import, history stays current through a fresh full
export of the source, imported incrementally. Four questions the architecture
left open are settled together, because they are one policy:

1. **The refresh model.** Each export carries the account's history in full
   rather than the changes since the last one, so a refresh is a new export
   placed under `data/` and a re-run of the import, needing no merge: the skip
   by source id and content hash (§17) confines the cost to what is new or
   changed. The only way a later export holds less than an earlier one is a
   conversation deleted in the source, which decision 3 governs. Should the
   source ever begin issuing deltas instead, this decision is the one to
   revisit. The export itself is requested by a person: no supported interface
   yields an account's conversation history, and driving an unsupported one
   would mean holding live credentials in a project whose Principle V exists
   because credentials in this corpus are hazardous. That is a property of the
   source, recorded here rather than treated as missing tooling. How the archive
   arrives is outside this decision — acquisition is a replaceable component
   whose default implementation is manual placement — so automating it later
   changes nothing below.
2. **A conversation that continued** is replaced in full. `update_mode:
   "replace"` stays the default for re-import, and `append` remains reserved for
   its §9 purpose of delivering one oversized document as several items. Where
   the two meet — a conversation both too large to send at once and grown since
   the last import — the whole conversation is re-sent within one retain
   request, its first item replacing and the remainder appending, which keeps
   the composition idempotent.
3. **A conversation that disappeared stays.** The importer MUST NOT diff the raw
   archive or the import state against an export, and MUST NOT derive removals
   from one. An absence may be recorded in the run log; nothing may act on it.
   Deliberate forgetting is a separate, human-initiated operation on a named
   `document_id`, reserved for content that must not be retained; it is out of
   scope for the MVP and belongs to no import path.
4. **The content hash covers content, not presentation.** The canonical
   representation hashed under §17 includes the messages, their order and the
   timestamps of the messages, and excludes the title and any metadata the
   importer itself produces.

**Rationale.** A full export makes a skip sufficient: nothing needs merging, and
the expensive part of an import is extraction per conversation, which §17
already avoids for everything unchanged. Replacing a grown
conversation rather than appending to it keeps re-import idempotent — a replay
from the raw archive, which Principle I requires to stay possible, would
otherwise append the same tail twice — and keeps extraction seeing the whole
conversation, as §7 intends.

Absence is not evidence of deletion. A truncated download, a partial export and
a deliberate deletion arrive as the same input, and no signal separates them.
The risk is asymmetric: a conversation wrongly kept costs some noise in recall,
while one wrongly removed is unrecoverable, because by then it is gone from the
source too. And were an absence able to empty the archive, the source service
would hold a remote delete over a store whose whole purpose is independence from
it (Principle I, ADR-001).

Excluding the title from the hash keeps a rename from costing a full
re-extraction; excluding importer-produced metadata keeps a version bump from
invalidating the entire corpus at once.

**Consequences.** Three costs, stated rather than softened. A conversation that
keeps growing is re-extracted in full on every refresh in which it grew. A
renamed conversation is skipped, so the title carried as metadata goes stale
until some other change re-imports it. A conversation deleted in the source
remains retrievable through memory, by design — and until deliberate forgetting
exists, rebuilding the bank is the only remedy for a secret the sanitizer
missed.

A fourth consequence follows from decision 4 and must not be discovered later.
Because importer-produced metadata is outside the hash, an ordinary refresh
after the parser, the sanitizer or the extraction policy has changed skips every
unchanged conversation and therefore does nothing. §3.1 and Principle I promise
that such a change can be re-applied to the whole archive, so that promise is
kept by an explicit forced re-import that ignores the skip — a path the import
state owes, not something an ordinary refresh performs.

The rule binds sources whose export cannot distinguish absence from deletion. A
source that carries an explicit deletion event is a different case, decided in
that source's own record (§2).

Memory ages between refreshes and nothing forces one, which is why the age of
the last import belongs in whatever the command surface reports: the decay is
made visible rather than prevented.

### ADR-008 — Consumers reach memory through hermes-memory's MCP server

ADR-007 is reserved for automated export acquisition (#40).

**Decision.** hermes-memory is the store of the user's AI history, and the only
component that talks to Hindsight. Consumers — Hermes first, then Claude Code
and Codex — connect to an MCP server that hermes-memory exposes, the memory
access surface of §16.1, and are not configured against Hindsight at all.
Settled together, because they are one policy:

1. **One surface, one module.** The server lives in a new module, `access`,
   which depends on `memory/interface`, the raw archive and the import state,
   and on nothing that knows Hindsight. It is a new §8 boundary, held to
   Principle IV like the others.
2. **Read-only.** The surface retrieves; it does not retain. Memory is written
   by importers only, and a consumer's own conversations reach memory as a
   history source with its own specification and record (§2). Hermes's native
   Hindsight provider is therefore used neither to read nor to write.
3. **Archive behind the facts.** Next to `recall`, the surface serves whole
   conversations from the raw archive by `document_id`, paged by message so a
   long one fits an agent's context. It serves the normalized form only; the
   original is the one unsanitized form and never leaves the process.
4. **Transport is stdio.** The consumer starts the server as a local process.
   It opens no port and holds no credential of its own, and several consumers
   may each run one against the same archive and Hindsight instance. A network
   transport is out of scope until a consumer cannot start a local process, and
   then needs authentication of its own and a record of its own.
5. **Grown by need.** The surface starts with `search_memory` and
   `get_conversation`. `reflect` and `list_conversations` arrive with the
   features that use them, and so does any method they need behind the
   boundaries — `memory/interface` holds no `reflect` until then.
6. **The SDK.** The server is built on the official MCP Python SDK, added to
   the stack in the constitution. FastAPI remains the choice for a non-MCP HTTP
   surface, which this decision does not introduce.

**Rationale.** ADR-001's exit strategy covered ingestion only. A consumer
configured against Hindsight — its native provider, its MCP endpoint or a
coding-agent integration — is coupled to the engine, its banks and its
vocabulary, and replacing the engine would mean reconfiguring every agent. With
one surface in front of it, the engine sits behind `memory/interface` for
consumers as well, and Principle IV holds on both sides of the system.

The surface also gives consumers what extracted memory cannot. `retain` is
lossy; a recalled fact is a pointer into a conversation, and only the raw
archive can return that conversation whole. Hindsight's own MCP endpoint would
be cheaper to adopt and would give neither of these.

Reads only, because a write path through a tool would break Principle I: a
memory written by a consumer straight into Hindsight has no original in the
archive, and cannot be re-extracted when the parser, the sanitizer or the
retain mission changes. A write tool that went through the pipeline would not
break it, but it would depend on the agent deciding to call it, and history that
is captured only when a model remembers to is history with holes. Importing a
consumer's sessions from where it keeps them is the reliable path, and is the
one §2 already prescribes for every source.

Stdio, because the consumers are local and single-user (§21): it needs no
authentication to get right, which a port on a machine holding years of private
history would.

**Consequences.** Recall stops being automatic. Hermes's native provider can
bring recalled memory into each turn by itself; through MCP, memory arrives only
when the agent calls a tool. How much of that the agent's own instructions
recover, and whether a thin automatic path is worth adding later, is for the
specification of the first surface to measure, not to assume.

Memory lags behind live work. A Hermes, Claude Code or Codex session is not
retrievable until its importer has run, so a refinement made in one agent
reaches another on the next import, not the next turn. Phase 2's acceptance is
worded accordingly.

There is one more component to run and test: the surface needs contract tests
like every §8 boundary, and an end-to-end test from a consumer's tool call to an
archived conversation. Phase 1 gains an item for it.

Each consumer starts its own server process, so archive and import-state access
is concurrent from the first day. Reads against SQLite and local files tolerate
that; it is a constraint on the production stores of ADR-004, which must allow
concurrent readers alongside a running import.
