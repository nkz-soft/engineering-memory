# Research: Coding-agent access

Research date: 2026-11-03. Planning research only; no live client acceptance claimed.

## R1 — Use the access server, not native engine integrations

**Decision**: Register `engineering-memory serve` in both clients.
**Rationale**: Constitution IV, ARCHITECTURE.md §16.1/§22 and ADR-008 require the
read-only surface and import-mediated cross-agent visibility. #25/#27/#28 are closed.
**Alternatives considered**: Native Hindsight integrations and per-repository banks
contradict current architecture; no governance change is necessary to follow ADR-008.

## R2 — Official client registration

**Decision**: Document Claude Code local-scope stdio registration and Codex user config.
**Rationale**: These official mechanisms launch the existing server without a new adapter.

Claude Code registration shape:

```sh
claude mcp add --transport stdio --scope local engineering-memory -- /absolute/path/to/uv run --locked --project /absolute/path/to/engineering-memory engineering-memory serve
```

Verify configuration with `claude mcp list`, `claude mcp get engineering-memory`,
then `/mcp` in a fresh session. Local scope is project-specific private configuration;
user scope is cross-project; project scope writes a shareable `.mcp.json` and requires
client approval. Never place literal tokens in persisted `--env` options.
Official source: [Claude Code MCP](https://code.claude.com/docs/en/mcp).

Codex configuration shape in `~/.codex/config.toml`:

```toml
[mcp_servers.engineering-memory]
command = "/absolute/path/to/uv"
args = ["run", "--locked", "--project", "/absolute/path/to/engineering-memory", "engineering-memory", "serve"]
env_vars = ["ENGINEERING_MEMORY_ARCHIVE_ROOT", "ENGINEERING_MEMORY_HINDSIGHT__BASE_URL", "ENGINEERING_MEMORY_HINDSIGHT__BANK_ID", "ENGINEERING_MEMORY_HINDSIGHT__TOKEN"]
```

Official config supports command/args/cwd, explicit env and forwarded env_vars.
`codex mcp list` checks registration; `/mcp` checks active servers. Trusted-project
configuration is an alternative; user config avoids committing personal paths/secrets.
Official source: [OpenAI MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

**Alternatives considered**: A committed machine-specific configuration is not portable;
new wrappers add maintenance without changing the access contract.

## R3 — Environment and paths

**Decision**: Reuse `docs/operations/hermes-memory.md` server prerequisites and explicit
absolute paths; document Windows forward-slash paths and environment forwarding.
**Rationale**: Both agents must reach the same archive/backend regardless of cwd.
Server settings use ENGINEERING_MEMORY_; extraction settings are for imports, not reads.
Secrets come from environment/local secret handling, never literal public examples.
**Alternatives considered**: Relying on caller cwd or implicit environment inheritance
makes the recipe fragile, especially for Codex's forwarded variable allow-list.

## R4 — Distinguish regression from real consumer acceptance

**Decision**: Add synthetic cross-source import-to-stdio regression and separately
record actual live Claude Code/Codex sessions. Include before-import absence, provenance,
context, negative filters and unchanged import checks.
**Rationale**: Existing SDK/backend gates prove neither client's tool invocation. Existing
source adapters are explicitly bounded dialects; an actual completed snapshot may expose
an unsupported variant, which must be recorded rather than rewritten into fake evidence.
**Alternatives considered**: Mocks/handwritten native transcripts are useful fixtures but
cannot prove the live-client acceptance. Private history is unnecessary and unsafe evidence.

All design unknowns resolved. Actual client/service readiness and supported live session
format remain implementation prerequisites, not unresolved product design choices.
