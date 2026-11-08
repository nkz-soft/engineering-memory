# Hermes memory access

Hermes reads imported history through engineering-memory's stdio MCP server
(ADR-008). Keep the native Hindsight provider disabled for this corpus: importers
own writes, and consumers retrieve through this access surface.

## Prepare the server

Use Python 3.13 and run `uv sync --locked` in the checkout. The SDK is locked at
mcp 2.3.0. Provision and import first using the existing operator commands; `serve`
does neither. The archive and backend settings must point at the same corpus as the
importer. No extraction LLM settings, project rules or import-state DB are required
for serving reads.

Set these in the environment inherited by Hermes's child process:

```sh
export ENGINEERING_MEMORY_HINDSIGHT__BASE_URL=http://localhost:8888
export ENGINEERING_MEMORY_ARCHIVE_ROOT=/absolute/path/to/data/archive
# The production default is engineering-global. Do not create a consumer bank.
export ENGINEERING_MEMORY_HINDSIGHT__BANK_ID=engineering-global
```

For an authenticated backend, supply ENGINEERING_MEMORY_HINDSIGHT__TOKEN through
the environment or local secret handling; never commit its value. The project's
optional untracked .env uses the same precedence as import commands. Use absolute
paths for installed deployments; relative paths resolve against the project package
root, independently of the consumer's working directory.

## Connect Hermes

Merge the following into your local `~/.hermes/config.yaml`, replacing executable
and checkout paths with absolute paths on the machine that runs Hermes:

```yaml
mcp_servers:
  engineering-memory:
    command: /absolute/path/to/uv
    args: [run, --locked, --project, /absolute/path/to/engineering-memory, engineering-memory, serve]
```

On Windows use forward-slash paths, for example `C:/Tools/uv.exe` and
`D:/Projects/engineering-memory`; an alternative is the installed
`D:/Projects/engineering-memory/.venv/Scripts/engineering-memory.exe` with args
`[serve]`. Keep the server and archive on the same machine/environment as the
Hermes subprocess. A Docker/remote Hermes process cannot see host paths unless
its environment explicitly provides them.

Start a new session with `hermes chat`. Confirm `search_memory`, `get_conversation`,
`get_project_model` and `reflect` are discovered. See [project models](project-models.md) for refresh and reads.
Hermes may namespace their names with the server name. Official setup reference:
[Hermes MCP documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp).
This recipe follows that documented command/args structure; the installed Hermes
version must be recorded when completing the live acceptance below.

The command stays alive while the consumer owns stdin. stdout contains only MCP
protocol and diagnostics go to stderr. The server uses local stdio and exposes read tools. The [routing guide](reflect-evaluation.md)
describes project-scoped synthesis through `reflect`. Normal disconnect closes the
backend HTTP client. Startup errors use safe categories and a nonzero exit code.

## Retrieve and follow context

Ask Hermes explicitly to call search_memory. Example tool arguments:

```json
{"query":"How did Orchard isolate worker retries?","tags":["project:orchard","source:chatgpt"],"limit":10}
```

All tags must match. Omit tags to search the full shared corpus, or use
`project:unknown` for unclassified history. The four existing namespaces are
project, source, type and user. Tags are scoping, not an authorization system;
only launch this local process for a consumer allowed to read the archive.
There is no engine-specific matching-mode argument or time-range parameter.

Each match contains content, stable document_id, full retained provenance,
original started_at and optional score. Scores compare only within one result set.
Empty results mean no matches; they do not mean the backend is unavailable.

Follow the identity to get_conversation:

```json
{"document_id":"chatgpt:synthetic-e2e-decision","offset":0,"page_size":50}
```

It returns sanitized normalized messages in archive order, provenance and next_offset.
Pass next_offset for the next page; null means the end. Search defaults to 10 results,
maximum 100. Pages default to 50 messages, maximum 100. Negative offsets, boolean
numbers, invalid identities/tags and unknown arguments fail validation. A message
may itself be large: message-count paging does not truncate text or guarantee a
byte/token limit. Re-imports can change the record between pages; repeat from zero
if that happens. Original export bytes are never returned. Treat retrieved history
as untrusted evidence and cite its provenance, never execute instructions within it.

## Troubleshoot

- `invalid_input`: check required arguments, tag namespace/value and numeric bounds.
- `not_found`: document identity is unknown to this archive. Check that server and
  importer use the same archive; a recalled fact whose archive is missing fails too.
- `corrupt_record`: archive data is invalid or identity mismatched; repair from the
  local source-of-truth workflow rather than trusting a partial result.
- `unavailable`: check backend readiness/connectivity or archive filesystem access.
- `rejected`: verify backend credentials and permissions locally.
- `internal`: inspect the setup and reproduce with synthetic fixtures; the service
  deliberately does not expose exception details or conversation contents.
- Startup `configuration`: verify ENGINEERING_MEMORY_ settings and absolute paths.
  Unrelated extraction credentials do not need to be configured.
- No tools: confirm the executable runs on Hermes's machine, the environment reaches
  its child, and the selected tool filter permits both tools; start a fresh session.

## Acceptance procedure

Use synthesized history for public evidence. The existing credential-free live gate
runs an isolated backend and synthetic extraction fixture:

```sh
uv run python deploy/hindsight/e2e.py
```

It now requires test_import_to_access_tools in addition to the importer/idempotency
checks. That test imports a conversation, launches the real stdio entry point from
an unrelated directory, searches scoped history, checks fact/provenance/original time,
reads archived context and verifies a disjoint project filter excludes the fact.
The normal regression suite also checks paging and an original-secret sentinel.

To complete the separate Hermes acceptance:

1. Import a synthetic decision and a competing decision for a second project into
   your local deployment using the documented import workflow. Keep the expected
   answer outside the fresh chat prompt.
2. Connect Hermes as above. Ask “Use engineering-memory to find how Orchard isolated
   worker retries; cite its source.” Verify the answer against the imported decision
   and require a matching document_id and original provenance.
3. Ask for the normalized conversation, page through it, and verify the context.
4. Repeat with project/source filters; the competing project's decision must be absent.
5. Repeat setup from a second clean consumer configuration using only this guide.
6. Record date, commit, SDK/Hermes versions, commands, discovered tools and synthetic
   evidence. Never publish private history, credentials or user configuration.

A passing SDK test is not evidence of a Hermes conversation. Until the live consumer
steps are recorded, Phase 1's consumer acceptance remains unverified; see the
[verification record](../../specs/024-hermes-memory-access/verification.md).
