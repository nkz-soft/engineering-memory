# engineering-memory

Long-term engineering memory shared across AI assistants.

Engineering Memory stores AI conversation history so assistants can recall past
technical decisions, investigations and reasoning without carrying them over by
hand. [Hermes](https://github.com/NousResearch/hermes-agent) is the first planned
consumer; Claude Code and Codex will use the same memory access surface. ChatGPT
exports are the first supported history source; other sources follow separately.

## Intended architecture

The complete import and retrieval flow is still being built. Conversation history
is exported, normalized into a source-independent model, stripped of secrets,
tagged with its project and provenance, and retained in
[Hindsight](https://github.com/vectorize-io/hindsight), which handles fact
extraction, the knowledge graph and retrieval.

Agents will reach the single shared memory bank through this project's read-only
MCP server, started locally over stdio. Consumers do not connect directly to
Hindsight.

```text
ChatGPT export ──► import pipeline ──┬──► raw archive (original + normalized)
                                    └──► Hindsight

Hermes / Claude Code / Codex ──stdio MCP──► memory access surface
                                           ├──► Hindsight (search)
                                           └──► raw archive (normalized only)
```

Originals are archived independently of Hindsight, so extraction can be re-run
with a better model, a different mission or a fixed parser without requesting
another export. Keeping the archive also makes the memory engine replaceable.
Only sanitized, normalized conversations are served to consumers.

## Status

The project is in development, built as a Python modular monolith with a
self-hosted Hindsight instance as the planned memory engine.

Implemented and tested: configuration, structured logging and tracing, normalized
conversation models, boundary interfaces, ChatGPT export parsing, secret
sanitization and deterministic project classification. CI covers tests, lint,
secret scanning and container packaging.

Persistent local archive, SQLite import-state, the Hindsight adapter and the
conversation-by-conversation ingestion pipeline are implemented. The operator CLI
provides provisioning, export import, archive replay and offline status. The MCP
access server remains future work. Synthetic live validation uses the isolated
Hindsight contract stack; it does not measure model quality on private history.

The first milestone is to import ChatGPT history and have Hermes answer a
question from it. Claude Code and Codex access, and additional history sources,
follow as separate work with their own specifications and decision records.

## Development

Python 3.13, managed with [uv](https://docs.astral.sh/uv/). With Git and uv
installed, uv provisions the interpreter from `.python-version`.

The examples below use a POSIX shell. Clone the repository, then install from
the committed lockfile:

```bash
git clone https://github.com/nkz-soft/engineering-memory.git
cd engineering-memory
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .

# Inspect the current command surface
uv run engineering-memory --help
uv run engineering-memory --version
```

CI runs the same locked installation, tests, lint and formatting checks on every
pull request. The tests use synthetic conversations; no private export, running
Hindsight instance or LLM credential is needed.

The module tree under `src/engineering_memory/` mirrors the layout recorded in the
[constitution](.specify/memory/constitution.md); a test checks that they agree.

## Secret scanning and the container image

Two further checks run in CI and need a container runtime. Without one you can
still run everything above, and CI remains the backstop for these two.

```bash
# Scan the whole history for credentials
docker run --rm -v "$PWD:/repo" -w /repo \
  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0='*' \
  ghcr.io/gitleaks/gitleaks:v8.30.1 git . --no-banner --redact -v

# Build the image and run its default help command
docker build -t engineering-memory:local .
docker run --rm engineering-memory:local
```

The image currently prints CLI usage and exits; it does not start an import or
an MCP server.

The scan reads the **history**, not the working tree, because a credential
committed and deleted in the next commit remains reachable. A finding fails CI.

**If the scan reports a finding, assume the credential is live.** Deleting it
from the diff does not help. Revoke it first, then remove it from history.

A finding is a false positive only if the value is synthetic and deliberate,
which here means a fixture proving that secrets get redacted. To declare one,
add an entry to [`.gitleaks.toml`](.gitleaks.toml) naming the rule, the file and
the literal — all three, never a directory. A test enforces that shape.

`tests/fixtures/secret_scanning/` is the opposite: a key that **must** be found.
CI scans it separately and fails if that scan comes back clean, proving the
check can fail at all.

## Configuration

The settings module reads only `ENGINEERING_MEMORY_`-prefixed configuration.
[`.env.example`](.env.example) lists every supported setting. To prepare a local
configuration, copy it and fill in your own values:

```bash
cp .env.example .env
```

Two variables are required when settings are loaded:

- `ENGINEERING_MEMORY_HINDSIGHT__BASE_URL`: the self-hosted Hindsight instance.
- `ENGINEERING_MEMORY_LLM__BASE_URL`: the OpenAI-compatible endpoint through
  which extraction will be routed.

Other settings have defaults or are optional. Tokens are optional because local
instances may run unauthenticated. Relative storage and rules paths resolve
against the repository root, not the current directory. A non-editable installed
deployment should use absolute paths; see [`.env.example`](.env.example).

`.env` is ignored by Git and must never be committed. Real environment variables
override the untracked file. Missing required values or malformed configuration
raise an error naming the variables at fault when settings are loaded.

The current help and version commands do not load settings or contact Hindsight.
Configuration alone does not enable import or retrieval while those components
are still pending.

### Project rules

Memory uses one shared bank, scoped by `project:` tags
([ADR-002](ARCHITECTURE.md#adr-002--one-shared-bank-projects-separated-by-tags)). The implemented classifier
uses local alias rules; [`projects.example.toml`](projects.example.toml)
documents their format:

```bash
mkdir -p data
cp projects.example.toml data/projects.toml
```

Each entry gives a project slug, literal aliases such as repository names or
paths, and an optional priority for conversations naming several projects.
Matching is whole and case-insensitive: `lantern` finds `example-org/lantern`
but not `lantern-api`; list both spellings when you want both.

The classifier returns `project:unknown` for no match or equal-priority matches
across projects. The planned importer will retain those conversations rather
than discard them.

The default file is under the ignored `data/` directory because rules contain
private project names and local paths. Override its location with
`ENGINEERING_MEMORY_PROJECT_RULES_PATH`. An explicitly configured missing file
is an error; an absent default file produces a warning and a classifier that
returns `project:unknown`.

Under the planned re-import policy, adding rules later does not automatically
reclassify unchanged conversations; see
[architecture §17](ARCHITECTURE.md#17-idempotency-and-import-state).

## Logging

The logging module emits JSON, one object per line, on standard error. Its
`ingestion_operation` context manager produces one terminal record carrying the
source, source id, project, bank, document id, start time, duration, status and
error. The production importer will use this helper when it is implemented.

**Credentials are never logged.** The logging pipeline redacts them by field
name, secret type and value pattern. A withheld value becomes `[redacted]`
rather than being dropped.

**Conversation contents are not logged by default.** Set
`ENGINEERING_MEMORY_LOGGING__INCLUDE_CONVERSATION_CONTENT=true` for a single
debugging run when needed. It puts private text wherever your log goes, so leave
it out of `.env`. Credentials remain redacted regardless of this setting.

`ENGINEERING_MEMORY_LOGGING__LEVEL` sets the level (`DEBUG` through `CRITICAL`,
default `INFO`). Both settings are documented in [`.env.example`](.env.example).

## Documentation

- [Architecture](ARCHITECTURE.md): intended design, boundaries, bank strategy,
  Hindsight contract, milestones and decision records.
- [Constitution](.specify/memory/constitution.md): principles, stack and review gates.
- [Feature specifications](specs/): specifications, plans, tasks and verification.
- [Issue-to-PR workflow](docs/workflow/issue-to-pr.md): taking work through planning,
  human review, implementation and a pull request.

## Migrating the project name

Install and invoke `engineering-memory` and import `engineering_memory`. Update
local environment files and process configuration to use `ENGINEERING_MEMORY_`
followed by the existing setting name, including nested `__` separators.
Consumer-prefixed variables are ignored; there is no compatibility fallback.

Update container image references and the Git remote:

```bash
git remote set-url origin https://github.com/nkz-soft/engineering-memory.git
```

The checkout directory may keep its current name. Keep archive paths, import
state, document IDs and the `engineering-global` bank unchanged; no data migration
or re-extraction is needed.

## License

See [LICENSE](LICENSE).

## Operator commands

Configure endpoints and paths using `.env.example` and the
[local Hindsight setup](docs/development/local-hindsight.md), then explicitly
provision the shared bank before importing. Credentials come from environment
configuration; no credential command-line flags are supported.

```sh
uv run engineering-memory provision
uv run engineering-memory import --export /path/to/export.zip
uv run engineering-memory import --from-archive --force
uv run engineering-memory status
```

| Command/flag | Meaning |
|---|---|
| `provision` | Apply and verify the retain mission on the configured shared bank. Import never provisions automatically. |
| `import --export PATH` | Read a ChatGPT ZIP, extracted export directory, or conversations JSON file. |
| `import --from-archive` | Replay originals from the configured local archive, with current processing rules. Select exactly one input mode. |
| `import --force` | Reprocess unchanged content explicitly; stable document ids are preserved. |
| `status` | Inspect latest local imported/failed records without contacting memory or requiring remote endpoint settings. Missing state is empty; corrupt state is an error. |
| `--json` | Per operational command, emit one versioned JSON result on stdout; logs use stderr. |
| `--help` | At root or on any command, list accepted arguments. |
| `--version` | At root, print the installed distribution version. |

`ENGINEERING_MEMORY_ARCHIVE_ROOT`, `ENGINEERING_MEMORY_IMPORT_STATE_PATH` and
`ENGINEERING_MEMORY_PROJECT_RULES_PATH` select local storage and classification
rules. Relative paths resolve against the source checkout, consistently with
existing settings; installed deployments should use absolute paths. Status reads
only the state-path setting. Provision/import validate the full configuration.

Import reports imported, skipped and failed counts plus safe per-item failures.
Unchanged successful conversations skip extraction; changed and failed items
retry. One item failure does not prevent later valid items from importing.
Status describes **latest durable records**, not historical runs: skips do not
overwrite imported records, and failures without usable identity may appear only
in the import result. Status can successfully report stored failures.

Exit codes: **0** success (including empty/all-skipped imports and successful
status inspection), **1** operational/configuration error or any import failure,
including partial success, **2** usage error, **130** interruption after cleanup.

```sh
uv run engineering-memory import --export /path/to/export.zip --json
uv run engineering-memory status --json
```

Structured results include `schema_version: 1`, `command`, `status` and `error`.
Import adds counts, outcomes and any terminal stage; status adds current records
and imported/failed totals; provision adds bank and mission verification. Error
categories/stages are fixed safe values, never arbitrary exception text. Framework
parser errors (unknown flags/invalid option types), help and version retain Typer
output. See the [CLI contract](specs/020-operator-cli/contracts/cli.md) for fields
and the [validation guide](specs/020-operator-cli/quickstart.md) for fixture/live
checks. Dry-run is deferred to #22.
