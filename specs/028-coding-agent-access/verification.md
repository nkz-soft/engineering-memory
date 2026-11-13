# Verification: Shared memory for coding agents

The original verification was recorded on 2026-11-03 for PR #70. The T014
follow-up below records the 2026-11-07 live client checks against `8c7629f`.
The [November 13 retry](#t014-retry-2026-11-13) verified authenticated Codex
startup. The before-import search remains unverified.

## Status

| Check | Status | Evidence |
|---|---|---|
| Specification quality | Pass | 16/16 existing checklist items; constitution gates pass |
| Test-first gate change | Pass | New omission test failed with DID NOT RAISE, then gate suite passed |
| Full regression | Pass | 2085 passed, 39 opt-in skips |
| Ruff lint/format | Pass | All checks passed; 512 files already formatted |
| Claude Code isolated registration | Pass | add/get/list exit 0; server reported Connected |
| Codex isolated registration | Pass | list/get exit 0; stdio registration and forwarded names accepted |
| Isolated live backend regression | Pass | 33 passed, no skips, including cross-source import-to-stdio |
| Actual ChatGPT -> Claude Code journey | Pass | Live Claude Code transcript shows scoped search and archived context for Orchard and Cypress |
| Actual Claude Code -> Codex refinement journey | Partial | Operator verified retrieval after import. Absence before import in a fresh Codex session remains unverified |

Real-agent acceptance is now tracked separately in [task #71](https://github.com/nkz-soft/engineering-memory/issues/71), consolidating T005/T008 as T014.
PR #70 supplies the configuration, isolated registration checks and backend regression.
The registration and SDK/backend results are from PR #70. The live journeys
have their own evidence and status under T014.

## Commands and results

```text
uv sync --locked
  Installed locked environment successfully (Python 3.13.15).

.venv/Scripts/python.exe -m pytest tests/unit/test_e2e_runner.py::test_cross_agent_case_cannot_be_omitted -q
  Before gate implementation: 1 failed — DID NOT RAISE ValueError.

uv run pytest tests/unit/test_e2e_runner.py -q --tb=short
  After gate implementation: 20 passed.

uv run pytest -q --tb=short
  2085 passed, 39 skipped in 106.74s.

uv run ruff check .
  All checks passed!

uv run ruff format --check .
  512 files already formatted.
```

Normal pytest skips opt-in backend cases by design. The separate isolated gate must
execute its required cases without skips before backend acceptance is passed.
Initial sandbox-only attempts could not access pytest/uv temp state or Docker; these
checks were rerun with the required local access. This was not a product failure.

## Client recipe checks

Installed versions: Claude Code 2.1.198, codex-cli 0.128.0, uv 0.12.5, MCP SDK 2.3.0,
Docker server 29.9.2. Official references were reopened on the verification date:
[Claude Code MCP](https://code.claude.com/docs/en/mcp),
[Codex MCP](https://learn.chatgpt.com/docs/extend/mcp).

Temporary client homes were explicitly isolated under ignored
`data/coding-agent-config-check/`; the first consumer working directory was inside that ignored subtree. The checks
were then repeated from a separate system temporary directory outside the checkout;
Claude add/get/list and Codex list/get all exited 0, and Claude reported Connected. No registrations were written into personal settings.
The child environment set an absolute synthetic archive path, bank engineering-global
and an intentionally unreachable backend `http://127.0.0.1:1`. This checks launch and
protocol startup, not successful backend retrieval.

With CLAUDE_CONFIG_DIR set only for these subprocesses:

```text
claude mcp add --transport stdio --scope local engineering-memory -- <absolute-uv> run --locked --project <absolute-worktree> engineering-memory serve
claude mcp get engineering-memory
claude mcp list
```

All three exited 0; get/list reported Connected. Configuration was written only into
the isolated home and scoped to the synthetic consumer directory. The command/args
recipe in the guide was used literally after substituting executable/checkout paths.

With an isolated CODEX_HOME containing only the guide's MCP TOML table and the same
explicit paths/environment variable names:

```text
codex mcp list
codex mcp get engineering-memory
```

Both exited 0; the entry was enabled, transport stdio, correct command/args and forwarded
ENGINEERING_MEMORY_ variable names. Codex's Auth Unsupported field describes MCP OAuth
support for this stdio registration; it is not a failure or evidence of model login.

## Initial live consumer blockers (2026-11-03)

`claude auth status` returned `loggedIn: false`, `authMethod: none` and firstParty provider.
No actual Claude Code conversation, native refinement snapshot, or cross-client answer
was generated. The two live journeys therefore remain blocked. The user selected
"Keep the PR draft with live acceptance blocked"; no login was attempted on their behalf.

The installed Codex CLI initially rejected the existing user config's priority service
tier (it accepts fast/flex). A **per-command** `service_tier="fast"` override allowed
`codex login status` to exit 0 and report authenticated; its credential-bearing output
was suppressed. No personal config edit or CLI upgrade was needed or performed. This
removes that config-reading obstacle but does not complete live refinement acceptance.

## Independent review

A separate reviewer inspected the tracked diff, new operations guide, regression and
tasks against the specification, plan and contract. No actionable correctness, security
or portability findings. Reviewer recommended a draft PR after successful checks and
honest evidence/status updates; actual live consumer acceptance is not merge-ready.

## Acceptance deferred from PR #70

After authenticated Claude Code is available, follow the operations guide with synthetic
history: blind ChatGPT decision recall, actual completed Claude Code refinement snapshot,
before/after import Codex visibility, provenance/time/context, project/source exclusions
and unchanged reimport. Record actual calls/results and tested versions, then request
review of the evidence before closing #71 and claiming Phase 2 acceptance. An unsupported native snapshot stays an explicit
blocker; the existing bounded parsers must not be silently expanded in this feature.
## Live-gate fixture debugging

The first gate attempt exposed a test setup error (duplicate uuid keyword); fixture
records were corrected to assign unique ids after construction and use explicit project
rules for ChatGPT records. A second attempt reached the refinement import but the
synthetic extraction service rejected a fact marker followed by another escaped line.
Its pytest worker was stopped after diagnosis; the supervisor exited nonzero and
cleaned the disposable run. The secret sentinel was moved to the separate user message,
leaving one supported fact marker in the assistant message. These failed attempts are
not counted as acceptance. The final gate outcome is recorded separately.

## Final isolated gate

```text
uv run python deploy/hindsight/e2e.py
  33 passed in 30.36s; no skips; required-case report accepted; exit 0.
```

The final run imported synthetic ChatGPT decisions in separate projects, observed no
Claude Code refinement before import, imported that source through the real pipeline,
then found it in a fresh stdio process. It checked original time/provenance, source and
project exclusions, sanitized two-page context and unchanged-import skipping without
another extraction call. Disposable engine banks/containers were cleaned up by the
existing gate. This is SDK/backend evidence, not a live coding-agent conversation.

Final lint/format checks passed after fixture correction (512 files); all local Markdown
links in the feature artifacts and changed operations/source guides resolve. Independent
review's evidence wording finding was resolved by repeating CLI checks from an actual
external temporary directory; stale quickstart wording was corrected.

Draft review: [PR #70](https://github.com/nkz-soft/engineering-memory/pull/70), implementation commit `4bd273c`. Issue #29 is in-review; T005/T008 remain blocked.

## Scope split

The user requested a separate task for integration testing on real agents. [#71](https://github.com/nkz-soft/engineering-memory/issues/71)
owns execution and evidence for both actual consumer journeys; T005/T008 remain
unverified and are consolidated under T014. #29/PR #70 retain the configuration guide,
isolated client checks and mandatory real-engine import-to-stdio regression. No new
live test was run during this documentation-only split, and no blocked check was marked
passed. The draft state of PR #70 is unchanged.

## T014 live client verification (2026-11-07)

Revision `8c7629fa0db00fbc8f069538e6605f079aed3c4f` on Windows. Local versions
checked while preparing this record were Claude Code 2.1.198, Codex CLI 0.128.0,
uv 0.12.5, Python 3.13.18 and MCP SDK 2.3.0.

### Setup and commands

The operator ran `uv sync --locked` and used the product Compose runner with
the internal LiteLLM profile. The operator mapped provider URL, model and key
from a private env file to `PRODUCT_PROVIDER_*`. The route used OpenRouter
through a Docker-reachable HTTPS proxy, and Hindsight reported ready on
`http://127.0.0.1:8889`.

```powershell
uv run --locked python deploy/product/run.py dependencies
Invoke-RestMethod http://127.0.0.1:8889/health/ready
uv run --locked engineering-memory provision --json
uv run --locked engineering-memory import --source chatgpt --export data/issue-71/chatgpt --dry-run --json
uv run --locked engineering-memory import --source chatgpt --export data/issue-71/chatgpt --json
```

The CLI used bank `engineering-global`, archive `data/issue-71/archive`, SQLite
state `data/issue-71/import-state.sqlite3` and rules `data/issue-71/projects.toml`.
The operator generated two records with `tests.synthetic.chatgpt_export`, using
IDs `issue71-orchard` and `issue71-cypress` and the expected decisions below.
The dry-run classified both records under their respective project tags.
Provision verified the retain mission and the import returned `imported: 2`,
`failed: 0` and exit 0.

From a separate consumer directory named `orchard`, the operator registered
Claude Code with `claude mcp add --transport stdio --scope local engineering-memory -- <uv> run --locked --project <checkout> engineering-memory serve`
and launched `claude`. Codex used the same stdio command, bank, local Hindsight
URL and archive. See the [client runbook](../../docs/operations/coding-agent-memory.md)
for the registration and configuration syntax.

### ChatGPT to Claude Code

The Claude Code transcript records `search_memory` with tags
`project:orchard`, `source:chatgpt`, followed by `get_conversation` on
`chatgpt:issue71-orchard`. The agent retrieved the synthetic cobalt relay
decision, original start time `2026-03-04T09:30:00Z` and ChatGPT provenance.
The positive control used `project:cypress`, `source:chatgpt`. The tool result
included `chatgpt:issue71-cypress` and excluded the Orchard document. Claude
Code opened the Cypress result and retrieved its violet queue decision.

### Claude Code to Codex

The operator captured a native Claude Code session containing the synthetic
rule to switch the cobalt relay to amber backoff after the third failed attempt.
The native snapshot recorded the service checkout as its working directory, so
the dry-run initially classified it as `project:hermes-memory`. The operator
added the recorded path as an Orchard alias in the test-only rules file. The
subsequent dry-run reported `project:orchard` and redaction category `password`.

```powershell
$snapshot = 'data/issue-71/claude-code/eec1be37-09ad-4dad-99bb-bedb758f5faf.jsonl'
uv run --locked engineering-memory import --source claude-code --export "$snapshot" --dry-run --json
uv run --locked engineering-memory import --source claude-code --export "$snapshot" --json
```

After import, the operator ran a fresh Codex session from the consumer directory.
The operator reported that `search_memory` with `project:orchard`,
`source:claude-code` retrieved the refinement. Codex opened
`claude-code:eec1be37-09ad-4dad-99bb-bedb758f5faf` with
`get_conversation(document_id, offset=0, page_size=1)` and followed
`next_offset` through offset 131 to the final null. The source was
`claude-code`, the session started at `2026-11-07T10:53:34.058Z`, and the
refinement message was recorded at `2026-11-07T10:55:28.958Z`. The returned
message displayed `password=[REDACTED]`. A Codex search with
`project:cypress`, `source:claude-code` returned an empty list. A search with
`project:orchard`, `source:chatgpt` returned the original ChatGPT document.

The archived Claude Code transcript contains two empty searches for the
refinement before import. The before-import result supplied by the operator
matches that transcript. A separate fresh Codex call before import remains
unverified. A follow-up attempt with a new synthetic question used
`codex -c 'service_tier="fast"' exec --skip-git-repo-check --sandbox read-only --json`.
The installed CLI failed before making a tool call. Its diagnostics reported
that it could not decode the model catalog's `max` reasoning level. The
noninteractive Claude Code retry also stopped at a login requirement.
T014 remains open for an authenticated, fresh Codex baseline before import.

### Unchanged snapshot re-import

On 2026-11-07, re-importing the unchanged Claude Code snapshot exited with code 0
and reported `imported: 0`, `skipped: 1`, and `failed: 0`. The document ID remained
`claude-code:eec1be37-09ad-4dad-99bb-bedb758f5faf`.

The [import pipeline](../../src/engineering_memory/ingestion/pipeline.py#L130)
returns `SKIPPED` before calling Hindsight `retain`, so this run did not initiate
another extraction. This was verified from the CLI result and the code path.
LiteLLM and OpenRouter request counts were not measured.

## T014 retry (2026-11-13)

Prerequisite checks ran on Windows against repository revision
`ecb30782117df7992acad521bcba73e792a3bae5`. Installed versions were Claude Code
2.1.198, npm Codex CLI 0.128.0, desktop-bundled Codex CLI 0.169.0-alpha.11.1,
uv 0.12.5, Python 3.13.18 and MCP SDK 2.3.0.

From an empty temporary consumer directory outside the service checkout:

```powershell
$cli = (Get-Command codex.exe).Source # Desktop-bundled executable
& $cli --version
& $cli exec --ignore-user-config --ignore-rules --ephemeral `
  --skip-git-repo-check --sandbox read-only --json `
  'Reply with exactly READY. Do not use tools.'
```

The bundled CLI returned `READY` and emitted `turn.completed` with exit 0.
Its diagnostics included a WebSocket HTTP 403. The npm CLI reported a
model-catalog decode error for reasoning level `max`, then its HTTP fallback
reported that the default model was unavailable with the signed-in account.
The bundled CLI is a verified way to start an authenticated turn for the next
attempt. The probe did not configure MCP or issue a memory tool call.

`claude auth status` returned `loggedIn: false` and `authMethod: none`. The
issue's previous backend refused connections at
`http://127.0.0.1:8889/health/ready`. A separate evaluation backend responded at
port 18897 and was left outside this retry. The existing archived refinement
was already imported during the November 7 run, so it cannot supply the new
before-import control.

Resume after Claude Code sign-in and backend preparation. Use a new synthetic
refinement and capture fresh Codex searches before and after importing its
completed Claude Code snapshot. T005 retains its November 7 pass. T008 and
T014 remain open.

## Secret-scan follow-up

CI flagged the intentionally invented password sentinel in test_coding_agent_access.py
(commit 4bd273c, generic-api-key). Reproduced with the pinned Gitleaks v8.30.1 image:
branch history scan exited 1 with that single finding. Added one AND allowlist entry
restricted to the exact rule, anchored test file and literal password sentinel; default
rules remain enabled. Removing the literal from the current tree would not repair a
history scan, so the fixture is retained and narrowly documented in .gitleaks.toml.

Validation:

```text
uv run pytest tests/structure/test_secret_scanning_config.py -q --tb=short
  5 passed
Gitleaks v8.30.1 git . --log-opts=028-coding-agent-access --no-banner --redact -v
  39 commits scanned, no leaks found, exit 0
Gitleaks v8.30.1 dir tests/fixtures/secret_scanning --no-banner --redact -v --exit-code 42
  negative-control aws-access-token detected, expected exit 42
```

Docker scans used read-only mounts of this worktree and shared Git metadata with
GIT_DIR/GIT_WORK_TREE and safe.directory configured for the container. The branch-history
scan used the updated worktree configuration. No runtime code or fixture content changed;
no repeat of model/backend tests was needed for this configuration-only correction.
