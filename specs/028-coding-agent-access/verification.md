# Verification: Shared memory for coding agents

The original verification was recorded on 2026-11-03 for PR #70. The T014
follow-up below records the 2026-11-07 live client checks against `8c7629f`.
The [November 13 retry](#t014-retry-2026-11-13) verified authenticated Codex
startup. The [November 20 retry](#t014-retry-2026-11-20) verified live Codex MCP
access to the synthetic ChatGPT corpus. The before-import refinement search
remains unverified.

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

## T014 end-to-end live client verification (2026-11-26)

The Windows 0.0.1 package from [package CI run 45352681627](https://github.com/nkz-soft/engineering-memory/actions/runs/45352681627)
was built from the same source tree as revision
`97b87b8f0889ac88b2d6a33471af36332fd6bc5a`. The packaged Python runtime
was 3.13.18. The release build installs locked dependencies, including MCP
SDK 2.3.0. Claude Code 2.1.332 was authenticated with an API key. Both
accepted Codex Desktop sessions used runtime `0.171.0-alpha.13.2` and ran
in a dedicated directory named `orchard` outside the checkout. Claude Code
started from the same directory. Both clients used the installed
`engineering-memory serve` read-only stdio endpoint and the same
`engineering-global` bank on local Hindsight 1.2.3. The importer alone
wrote to memory.

### Seed and live Claude Code retrieval

Create two synthetic ChatGPT export records using the shape from
`tests/synthetic/chatgpt_export.py`. Give each record a user message naming
its project, mentioning the cobalt relay worker retry policy and carrying
a fake `password=` value for the redaction check. Give each an assistant
message saying that after a failed health check, retries enter quarantine
for the period below. Set the record and first message timestamps to the
listed start and the second message timestamp to one second later.

| Export ID | Project and alias | Start time (UTC) | Quarantine |
| --- | --- | --- | --- |
| `issue71-20261126-orchard` | `orchard` | `2026-03-20T10:00:00Z` | 14 minutes |
| `issue71-20261126-cypress` | `cypress` | `2026-03-20T11:00:00Z` | 26 minutes |

Put the export in `$root/chatgpt/conversations.json`. In
`$root/projects.toml`, put one `[[project]]` rule per project, with
`project` and its single `aliases` entry set to the slug above. Run these
commands in a dedicated PowerShell process from the checkout:

```powershell
$root = (Resolve-Path 'data/issue71-full-20261126').Path
$env:ENGINEERING_MEMORY_PROJECT_RULES_PATH = Join-Path $root 'projects.toml'
$em = Join-Path $env:LOCALAPPDATA 'Programs/EngineeringMemory/engineering-memory.exe'
& $em import --source chatgpt --export "$root/chatgpt" --dry-run --json
& $em import --source chatgpt --export "$root/chatgpt" --json
```

The dry-run found both project tags and the `password` redaction category
for both records. The real import returned `imported: 2, failed: 0`.

Launch `claude` from the external `orchard` directory and ask for the
quarantine duration without giving the answers. The native Claude Code log
records one `search_memory` call per project, with `source:chatgpt` and
`project:orchard` or `project:cypress`. Each returned its own document and
excluded the other project's document. Claude opened both documents with
`get_conversation`, `page_size=1`, offsets 0 and 1. The tool returned the
start time and ChatGPT provenance, and the pages contained the seed
decisions and `password=[REDACTED]`. Neither successful tool result exposed
the fake password value.

The first read passed `project` without `snapshot` and returned
`invalid_input`. Claude Code Auto mode blocked subsequent read attempts.
The operator explicitly authorized the two synthetic document IDs in the
same session and retried with only document ID, offset and page size. The
next calls succeeded.

### Live refinement before and after import

In that same Claude Code session, add this synthetic clarification for
Orchard and ask Claude to confirm it. After two consecutive failed health
checks, wait 73 seconds before a trial retransmission. Keep the existing
14-minute quarantine. The marker is `EM-ISSUE71-ORCHARD-AMBER-1126`.

While Claude Code is still open, start a fresh local Codex Desktop chat
in the external directory. Ask about the marker and the trial
retransmission without supplying the answer, using `source:claude-code`
and `project:orchard`. The native Codex trace shows two searches with zero
results before import. A separate initial attempt ran from the checkout
and is excluded from the acceptance evidence.

Exit Claude Code with `/exit` and stage the complete main-session JSONL
under the ignored `$root/native` directory. Compare its SHA-256 with the
source file. Use the same PowerShell settings as for the seed:

```powershell
$snapshot = Join-Path $root 'native/d40f3bbb-fdac-4152-aace-9d259f1f714f.jsonl'
& $em import --source claude-code --export $snapshot --dry-run --json
& $em import --source claude-code --export $snapshot --json
```

The dry-run returned `would_import: 1, failed: 0` with
`project:orchard` and the `password` redaction category. The real import
returned `imported: 1, failed: 0` with no pending or uncertain work.

In a different fresh local Codex Desktop chat in the same external
directory, ask the same blind question. The native trace confirms
scoped `search_memory` and paged `get_conversation` with `page_size=4`. Codex
recovered the rule and the marker from document
`claude-code:d40f3bbb-fdac-4152-aace-9d259f1f714f`. Its original start
was `2026-11-26T13:39:55.691Z` and provenance was `claude-code`,
`project:orchard`. The refinement was in the page at offset 120 with
timestamp `2026-11-26T14:10:57.919Z`. The confirmation was at offset 124
with timestamp `2026-11-26T14:11:17.133Z`.

The live Codex trace records both negative controls. With
`source:claude-code` and `project:cypress`, the search returned no
results. With `source:chatgpt` and `project:orchard`, it returned the
original ChatGPT document and excluded the refinement. The separate
Cypress seed lookup in Claude Code was the positive control for the
other project.

Repeat the unchanged Claude Code import command. The final run reported
`imported: 0, skipped: 1, failed: 0` with the same document ID. The import
log recorded no `retain` operation on the repeat, consistent with the
pipeline skipping before retain. Provider request counts were not
measured.

The live ChatGPT-to-Claude-Code and Claude-Code-to-Codex journeys both
passed in this run. Supporting evidence is summarized here from the actual
client and importer logs. Raw native snapshots, local settings and
credentials are kept out of Git.

## T008 live client verification (2026-11-26)

The Windows 0.0.1 package was built from the same source tree as repository
revision `97b87b8f0889ac88b2d6a33471af36332fd6bc5a`. Claude Code 2.1.332
was authenticated using an API key. The two Codex Desktop sessions recorded
client version `0.171.0-alpha.13.2` and ran outside the service checkout.
Engineering Memory used its read-only stdio MCP server, the
`engineering-global` bank and Hindsight 1.2.3.

1. Open Claude Code in a dedicated directory named
   `issue71-t008-opal-relay` outside the checkout. Discuss the synthetic
   rule marked `EM-T008-OPAL-1126`: after the fourth consecutive failure,
   pause retransmission for 41 seconds. Keep the session open.
2. In a fresh local Codex Desktop chat, ask for the rule without stating it.
   Use tags `source:claude-code` and `project:issue71-t008-opal-relay`.
   The native Codex record shows two `search_memory` calls using these tags.
   Both returned empty results.
3. Exit Claude Code with `/exit`. Copy its complete main-session JSONL to
   the ignored staging directory below. Verify that SHA-256 matches the
   source file, then run the dry-run and import. The dry-run reported
   `would_import: 1` and `failed: 0` with the expected project tag. The
   real import reported `imported: 1` and `failed: 0`.

   ```powershell
   $snapshot = 'data/issue-71-t008/native/8cf089a2-a9ce-47f2-acf6-f66dee1618ba.jsonl'
   engineering-memory import --source claude-code --export $snapshot --dry-run --json
   engineering-memory import --source claude-code --export $snapshot --json
   ```

4. Ask the same blind question in another fresh local Codex Desktop chat.
   The native record shows a scoped `search_memory` call and
   `get_conversation` calls with `page_size=2` at offsets 0, 2 and 4.
   Codex found the marker and rule, with document ID
   `claude-code:8cf089a2-a9ce-47f2-acf6-f66dee1618ba`, start time
   `2026-11-26T13:07:08.156000Z` and Claude Code provenance. The dry-run
   recorded zero redaction categories for this synthetic session.
5. In a separate Codex MCP check, searching for the Opal marker with a
   different project or with `source:codex` excluded the Opal document.
   The other project, `project:agent-import-check`, was checked positively:
   with `source:claude-code`, it returned the synthetic Copper Gate record
   `claude-code:46cd59a6-d16a-4e1f-8e40-b9a81cf0a2c6`.
6. Repeat the unchanged import command from step 3. It reported
   `imported: 0`, `skipped: 1`, `failed: 0` and the same document ID.
   The CLI log contained no retain operation for the repeat; provider
   request counts were not measured.

Only synthetic IDs and summarized tool outcomes are included here. The
native transcripts and local importer reports remain untracked.

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

From a temporary consumer directory outside the service checkout, set `$cli`
to the full path of the desktop-bundled `codex.exe` and verify the version
before running the probe:

```powershell
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

## T014 retry (2026-11-20)

Windows, checked out from `origin/main` at
`a1ea3b7eb98dc4b5cb165f63a3059840dc8e08d2`. The previous worktree branch
`docs/verify-codex-refinement` remains at `5cf55b9`. Versions observed:
Claude Code 2.1.198, desktop Codex CLI 0.169.1, npm Codex CLI 0.128.0,
uv 0.12.5, Python 3.13.18, MCP SDK 2.3.0, Docker server 29.9.3 and
Hindsight 1.2.0 (digest pinned in `deploy/hindsight/service.yaml`).

| Check | Result |
|---|---|
| ChatGPT to Claude Code (T005) | November 7 pass remains on record. The new Claude Code run is blocked by sign-in. |
| Live Codex MCP preflight | Pass. A fresh authenticated Codex turn searched the two imported ChatGPT decisions and paged their sanitized contexts. |
| Fresh Codex baseline and recall of a new native Claude Code refinement (T008/T014) | Unverified. No new native refinement was produced or imported. |

### Isolated corpus and client commands

The old port 8889 did not accept a TCP connection. The following commands
built a separate loopback test corpus with a Docker volume unique to this
Compose project, a separate local archive and SQLite state, and the existing
contract extraction fixture. Hindsight, the importer and the stdio server
were real. The extractor generated facts from explicitly marked synthetic text.

```powershell
uv sync --locked
$env:CONTRACT_ENGINE_PORT = '18771'
$env:CONTRACT_FIXTURE_PORT = '18772'
docker compose -p engmem-issue71-20261120 -f deploy/hindsight/compose.contract.yaml up -d --wait --wait-timeout 150
$data = 'data/issue-71-20261120'
New-Item -ItemType Directory -Force $data | Out-Null
```

Save the following as `$data/prepare.py` and pipe its contents to
`.venv/Scripts/python.exe -` from the checkout. Keep the export and expected
answers outside the consumer working directories.

```python
from pathlib import Path

from tests.synthetic import chatgpt_export as export
from tests.synthetic import projects

root = Path("data/issue-71-20261120")
cases = (
    ("orchard", "Orchard uses a copper latch to isolate worker retries.", 1774000800),
    ("cypress", "Orchard competitor uses a silver queue to isolate worker retries.", 1774004400),
)
export.write_directory(
    root / "chatgpt",
    [
        export.linear_record(
            f"issue71-20261120-{project}",
            export.message(
                "user",
                f"{project.title()} worker retry policy. password=synthetic-issue71-demo",
                create_time=timestamp,
            ),
            export.message(
                "assistant",
                "Synthetic contract fact: " + decision,
                create_time=timestamp + 1,
            ),
            title=f"{project.title()} worker retries",
            create_time=timestamp,
        )
        for project, decision, timestamp in cases
    ],
)
(root / "projects.toml").write_text(
    projects.document(projects.entry("orchard"), projects.entry("cypress", priority=10)),
    encoding="utf-8",
)
```

Use a dedicated PowerShell process for these environment settings.

```powershell
Get-Content "$data/prepare.py" -Raw | & .venv/Scripts/python.exe -
Get-ChildItem Env:ENGINEERING_MEMORY_* | ForEach-Object {
    Remove-Item -LiteralPath "Env:$($_.Name)"
}
$root = (Resolve-Path $data).Path
$service = (Resolve-Path .venv/Scripts/engineering-memory.exe).Path
$env:ENGINEERING_MEMORY_ARCHIVE_ROOT = Join-Path $root 'archive'
$env:ENGINEERING_MEMORY_IMPORT_STATE_PATH = Join-Path $root 'import-state.db'
$env:ENGINEERING_MEMORY_PROJECT_RULES_PATH = Join-Path $root 'projects.toml'
$env:ENGINEERING_MEMORY_HINDSIGHT__BASE_URL = 'http://127.0.0.1:18771'
$env:ENGINEERING_MEMORY_HINDSIGHT__BANK_ID = 'engineering-global'
$env:ENGINEERING_MEMORY_LLM__BASE_URL = 'http://127.0.0.1:18772/v1'
& $service import --source chatgpt --export "$root/chatgpt" --dry-run --json
& $service provision --json
& $service import --source chatgpt --export "$root/chatgpt" --json
$before = (Invoke-RestMethod http://127.0.0.1:18772/stats).calls
& $service import --source chatgpt --export "$root/chatgpt" --json
$after = (Invoke-RestMethod http://127.0.0.1:18772/stats).calls
```

The dry-run reported two candidates with the expected project tags and
`password` redactions. Provision verified the retain mission. The first
import reported `imported: 2, skipped: 0, failed: 0`. The unchanged ChatGPT
reimport reported `imported: 0, skipped: 2, failed: 0` with the same IDs.
The extractor counter stayed at 2. The Claude Code reimport check remains due.

In an external temporary consumer directory named `orchard`, set
`CLAUDE_CONFIG_DIR` to `$root/claude-home` and run:

```powershell
claude mcp add --transport stdio --scope local engineering-memory -- "$service" serve
claude mcp list
claude auth status
```

Registration and the MCP health check succeeded. Auth status exited 1 with
`loggedIn: false` and `authMethod: none`. No login was initiated.

### Live Codex MCP preflight

`Get-Command codex.exe -All` identified the bundled executable under
`C:/Program Files/WindowsApps/OpenAI.Codex_26.1111.9664.0_x64__2p2nqsd0c76g0/app/resources/codex.exe`.
The bundled executable completed a repeat of the November 13 READY probe and the fresh
MCP turn below. Both used an external temporary directory, per-command config
and ephemeral sessions. The MCP turn reported transient connection errors
before completing successfully with exit 0.

The local launcher `$data/codex-check.py` passed the following argument
vector after the executable. JSON-encode the strings and arrays for the
TOML overrides and pass each override as one argument. The launcher used
Python's `subprocess.run` to preserve Windows argument quoting and captured
stdout to `$data/codex-smoke.jsonl`.

```text
exec --ignore-user-config --ignore-rules --ephemeral --skip-git-repo-check --sandbox read-only --json
-c mcp_servers.engineering-memory.command="<absolute path to .venv/Scripts/engineering-memory.exe>"
-c mcp_servers.engineering-memory.args=["serve"]
-c mcp_servers.engineering-memory.env_vars=["ENGINEERING_MEMORY_ARCHIVE_ROOT","ENGINEERING_MEMORY_HINDSIGHT__BASE_URL","ENGINEERING_MEMORY_HINDSIGHT__BANK_ID","ENGINEERING_MEMORY_HINDSIGHT__TOKEN"]
-c mcp_servers.engineering-memory.required=true
<one prompt argument>
```

The prompt asked only for worker retry isolation, searching ChatGPT with
the Orchard and Cypress project filters, then opening each returned ID
and paging through it. The JSON log contained six completed
`mcp_tool_call` events and `turn.completed`:

| `search_memory` tags, query `worker retry isolation` | Only returned document | Original start (UTC) | Decision |
|---|---|---|---|
| `project:orchard`, `source:chatgpt` | `chatgpt:issue71-20261120-orchard` | `2026-03-20T10:00:00Z` | Copper latch |
| `project:cypress`, `source:chatgpt` | `chatgpt:issue71-20261120-cypress` | `2026-03-20T11:00:00Z` | Silver queue |

`get_conversation` used `page_size: 1` and offsets 0 and 1 for each
document. The corresponding `next_offset` values were 1 and null.
Both returned matching IDs and provenance (source `chatgpt`, native source
ID, expected project and importer version `0.1.0`), the original start
time, and `password=[REDACTED]` on the first page. The second pages
contained the respective decisions. The fresh Codex baseline must search
for a unique refinement discussed in Claude Code before the native
snapshot enters the corpus.

### Independent backend regression

With plugin autoload disabled, the isolated gate passed with exit 0:
36 passed in 49.79 seconds, with no skips.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
& .venv/Scripts/python.exe deploy/hindsight/e2e.py
```

This separate gate exercises importer and SDK-to-stdio behavior with
synthetic extraction and a disposable engine. It does not use coding-agent
accounts.

### Resume live acceptance

Sign in with `claude auth login` using the isolated test profile
(`$data/claude-home`). The local `$data/claude-environment.ps1` sets the
profile and enters the external Orchard workspace. Then follow the
[two Phase 2 journeys](../../docs/operations/coding-agent-memory.md#demonstrate-the-two-phase-2-journeys).
Use a new refinement and preserve the complete, quiescent native snapshot
unchanged. The contract extractor accepts a bounded marked fact. If the
native transcript exceeds that fixture's contract, use a real extraction
provider on an isolated backend and repeat the before/after sequence in
that corpus.

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
