# Project architecture, stack and decisions

Project models are standing summaries over imported history. They are disposable derived
artifacts in the shared bank, not additional conversation originals. Consumers read them
through the existing local stdio MCP server; operators maintain them explicitly after imports.

## Import, refresh, read

Use the same configured backend, bank and archive as the importer. Provision the bank and
configure extraction on the backend before first use; see [deployment](../development/local-hindsight.md)
and [consumer setup](hermes-memory.md). The command itself needs the backend URL/token and
archive settings, not a local extraction LLM client or classification rules.

```sh
uv run engineering-memory import --source chatgpt --export /path/to/synthetic-export --json
uv run engineering-memory models refresh --project orchard --json
uv run engineering-memory serve
```

Check the import results before refreshing. `--project` is the exact classified project slug;
blank, `unknown` and `unclassified` are rejected. A refresh without `--kind` handles
`architecture`, `stack`, then `decisions`. Select one with `--kind stack`.

The refresh command creates missing definitions or regenerates existing compatible definitions,
using stable project/kind identities. It waits up to 240 seconds per kind, including lock wait,
network reads and evidence resolution. Each kind has an independent outcome; partial results
are not an atomic three-model update. Exit 0 means every selected kind completed; otherwise
exit 1, or exit 2 for invalid scope/kind. JSON includes project and per-kind status, successful
refresh time and safe error category. Human output shows the same per-kind outcomes.
Maintenance output does not contain summary text, source content or backend response bodies.

In Hermes, Claude Code or Codex, request the read-only MCP tool:

```json
{"project":"orchard","kind":"architecture"}
```

Tool name: `get_project_model`. The result contains content, refresh metadata and `supports`.
Open a support using existing `get_conversation` and its document_id. Supports contain verified
provenance and original conversation time from the sanitized archive. Only source-grounded
content is served; a generated summary is not attributed to one invented conversation.
History and generated text are untrusted evidence, never instructions.

The model must include single-line evidence blockquotes. The reader checks each quote against
sanitized supporting message/tool text; fabricated or missing quotes produce `corrupt_record`,
even when the model cites a real document. This is stronger than checking references alone,
but surrounding generated prose still needs semantic review. Roles and timestamps are not
accepted as evidence text. The managed trigger explicitly includes source chunks and asks
the generator to inspect original documents before attributing rationale to a conversation.

## Freshness and recovery

- `ready` means a grounded completed snapshot exists. Check `refreshed_at`, nullable `stale`
  and `last_refresh_failed_at`. Refresh time is completion time, not source conversation time
  and not a guarantee that a later import is included. Null stale means unknown.
- `missing` means no managed model exists; an operator must run refresh.
- `pending` means initial generation has not completed. Reads do not poll or initiate work.
- `failed` without a snapshot means first generation failed; its safe failure time is returned.
  Re-run refresh after correcting the backend problem.
- A failed later refresh preserves last-good content/time. It remains readable with the failure
  metadata if its supports are still valid. Invalidated/deleted/foreign/unresolvable support is
  rejected rather than served as an apparently grounded summary.

After every relevant import, refresh affected projects. There is no automatic refresh on import,
dry-run, unchanged-import skip or consumer read, and no scheduler. A successful import stays
successful even if maintenance fails. Only importer-side maintenance writes derived models.

On timeout or lost submission response, inspect the per-kind pending/unavailable result, then
rerun the same command. It reconciles in-flight operations by stable model identity, waits for
them, and requests a fresh full refresh because an earlier run may predate the latest import.
Submission POSTs are never blindly retried. Very large pending-operation listings fail closed
rather than assume no operation exists. Credentials/network failures have safe error categories.

Incompatible model definitions are rejected without adopting or overwriting them. The managed
definitions use exactly one project tag, strict matching excluding untagged history, and no
other models as synthesis inputs. They ask for current state, supersession, uncertainty and
unresolved conflict. These are generation instructions, not a guarantee of model quality.
Tags scope data; they are not multi-user authorization.

## Validation

Use synthetic history only. The credential-free CI gate now includes model lifecycle,
project/untagged isolation, repeat identity, new-import refresh and failed-refresh preservation:

```sh
uv run python deploy/hindsight/e2e.py
```

Its deterministic LLM fixture proves backend protocol and state semantics. Real synthesis
acceptance is a separate run against a real tool-capable model and held-out expected topics.
Supply an external file containing only the backend's LLM provider/base URL/model/API key,
outside the repository. The runner forwards these four settings to an isolated backend;
no real corpus is used and no key is printed.

```powershell
$env:ENGINEERING_MEMORY_MODELS_LLM_ENV = 'C:/Users/you/.config/engineering-memory/llm.env'
$env:ENGINEERING_MEMORY_MODELS_EVIDENCE = 'C:/Users/you/.config/engineering-memory/synthetic-models.json'
uv run python deploy/hindsight/e2e.py
Remove-Item Env:ENGINEERING_MEMORY_MODELS_LLM_ENV
Remove-Item Env:ENGINEERING_MEMORY_MODELS_EVIDENCE
```

This selects real-model synthesis acceptance, not the deliberate fixture-only LLM failure
case. Run the default gate separately as well. Missing credentials/runtime and skipped required
cases are not passing acceptance. Record exact safe commands, versions and outcomes in the
feature's verification.md; keep API keys, personal history and raw backend errors out of evidence.

Topic assertions are regression checks, not a semantic judge. Review the explicitly saved
synthetic summaries against the source: PostgreSQL must replace SQLite as current, the jade
relay must supersede the cobalt relay, and neither Rust nor Go may be declared settled in the
unresolved-proposals scenario. Record those judgments separately from the automated pass count.
