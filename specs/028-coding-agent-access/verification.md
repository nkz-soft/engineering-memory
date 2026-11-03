# Verification: Shared memory for coding agents

Date: 2026-11-03. Branch: `028-coding-agent-access`, based on `8ef0825`; planning
commit `38a17ad`. Implementation revision is the commit containing this record.

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
| Actual ChatGPT -> Claude Code journey | Blocked | Claude Code reports loggedIn=false |
| Actual Claude Code -> Codex refinement journey | Blocked | Requires the authenticated completed Claude Code session from the first journey |

The user explicitly requested keeping the PR draft with live acceptance blocked.
Both actual consumer conditions remain unverified. Registration and SDK/backend checks
are not model-driven client acceptance. Do not merge or claim Phase 2 complete on these
results alone. No personal client settings, private history or credentials were changed.

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

## Live consumer blockers

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

## Remaining acceptance

After authenticated Claude Code is available, follow the operations guide with synthetic
history: blind ChatGPT decision recall, actual completed Claude Code refinement snapshot,
before/after import Codex visibility, provenance/time/context, project/source exclusions
and unchanged reimport. Record actual calls/results and tested versions, then request
review before marking the PR ready. An unsupported native snapshot stays an explicit
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
