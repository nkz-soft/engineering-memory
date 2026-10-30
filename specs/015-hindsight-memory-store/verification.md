# Phase 2 Verification Record

## 2026-10-29 — Resume and foundational prerequisites

Resumed the existing committed plan on branch 015-hindsight-memory-store at 9a1f53f following the repeated issue-to-pr invocation. No new worktree or feature number was created. The requirements checklist has no unchecked entries. No extension hooks are installed.

Generated tasks.md through the Spec Kit task workflow and validated discovery with:

```text
.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
```

Result: feature directory and all design artifacts discovered successfully.

## External compatibility gate unavailable

- docker version --format '{{.Server.Version}}': no docker_engine named pipe.
- docker context ls: default and desktop-linux contexts exist; DOCKER_HOST overrides the default.
- docker --context desktop-linux version --format '{{.Server.Version}}': no dockerDesktopLinuxEngine named pipe.
- docker --context desktop-linux ps: same missing-pipe failure.
- docker compose -f deploy/hindsight/compose.yaml ps: required HINDSIGHT_API_LLM_BASE_URL, HINDSIGHT_API_LLM_MODEL and HINDSIGHT_API_LLM_API_KEY are missing in this process. No secret values were printed.

The explicit desktop-linux context avoids mistaking the overridden default context for a stopped daemon. An unsandboxed read-only daemon check is also requested to rule out sandbox access restrictions.

No container was started, no bank was written, and no live API behavior was validated. Docker plus an operator-configured LiteLLM route, or an already running authorized test instance, is required to execute the compatibility gate. No credentials should be supplied in chat.

## Progress and limits

T001 and T002 are complete. T003 remains open until exact pinned request/response schemas are recorded; T004 requires the unavailable instance. Adapter code, red/green implementation tests, live contract verification, code review and PR remain outstanding. No passing implementation or completion claim is made. Existing architecture paths remain unchanged until verified.

Unsandboxed desktop-linux version/ps checks also failed with the same missing named pipe; this is not a sandbox-only access failure. Task list validation found 20 checklist tasks. git diff --check passed.

## 2026-10-30 — Source compatibility research and deployment recheck

Resumed the clean existing worktree at dd57217. Prerequisite discovery with
`.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks`
succeeded; requirements checklist has no unchecked items and no extension file is tracked.

Docker availability changed: unsandboxed `docker --context desktop-linux version
--format '{{.Server.Version}}'` returned 29.9.2, and `docker --context desktop-linux
ps --format '{{.Names}} {{.Status}} {{.Ports}}'` succeeded with no running containers.
The default-context sandbox check reported permission denied; explicit-context
unsandboxed checks establish that the daemon is reachable.

`docker compose -f deploy/hindsight/compose.yaml config --quiet` failed because
HINDSIGHT_API_LLM_BASE_URL, HINDSIGHT_API_LLM_MODEL and HINDSIGHT_API_LLM_API_KEY
are missing. Only variable names were inspected; no credential values were printed.
No container or bank was created.

T003 is complete: GitHub API source inspection at the immutable upstream revision
recorded in research.md establishes the HTTP request/response shapes. T004 remains
blocked on an operator-configured LiteLLM route and credentials. Required live
semantics have not been proven; source inspection cannot replace that evidence.
The approved dependency sequence therefore still blocks adapter implementation
and PR delivery. Configure those variables in the execution environment, then
resume `/issue-to-pr 16`. Do not put credentials in chat or committed files.

## 2026-10-30 — Correct deployment prerequisite after issue #55

The preceding engine-only preflight did not account for merged issue #55 / PR
#56. Merged main (17ac51a) into this feature branch without conflicts. The product
Compose stack now supplies the internal proxy URL and engineering-extraction
alias, and maps PRODUCT_PROXY_KEY into the engine credential. The three legacy
HINDSIGHT_API_LLM_* variables are therefore not prerequisites for this workflow.

Validation from this worktree:

- `uv run python deploy/product/run.py config`: OK: config, exit 0.
- `uv run python deploy/product/run.py dependencies`: FAIL: Missing required
  variable: PRODUCT_PROXY_KEY, exit 1 before container creation.

No PRODUCT_* environment variables or deploy/product/.env were found in this
worktree. The primary checkout and issue #55 worktree also have no product .env.
Internal mode requires PRODUCT_PROXY_KEY, PRODUCT_PROVIDER_MODEL,
PRODUCT_PROVIDER_API_BASE and PRODUCT_PROVIDER_API_KEY, per the new deployment
guide. External mode instead needs PRODUCT_PROXY_URL and PRODUCT_PROXY_KEY.
The remaining prerequisite is operator provider configuration, not an independently
deployed LiteLLM proxy. T004 still has no live evidence.

## 2026-10-30 — Required OpenRouter network proxy

Operator selected OpenRouter openai/gpt-oss-20b and supplied the provider key in
the ignored product .env. Startup was interrupted following the operator's
requirement that OpenRouter always be reached through environment-configured
network proxies. No product containers were running when checked afterward.

Added regression tests for proxy forwarding and missing/bypassed OpenRouter
proxy configuration. Both failed before the change (2 failed). Compose now
forwards HTTP_PROXY, HTTPS_PROXY, ALL_PROXY and NO_PROXY to LiteLLM, including
lowercase fallbacks. Internal OpenRouter preflight requires HTTPS_PROXY or
ALL_PROXY and rejects NO_PROXY bypass of openrouter.ai.

Verification:

- `uv run pytest tests/unit/test_product_runner.py tests/structure/test_product_deployment.py -q`: 33 passed.
- `uv run ruff check deploy/product/run.py tests/unit/test_product_runner.py tests/structure/test_product_deployment.py`: all checks passed.
- `uv run ruff format --check deploy/product/run.py tests/unit/test_product_runner.py tests/structure/test_product_deployment.py`: 3 files already formatted.
- `git diff --check`: passed.
- `uv run python deploy/product/run.py dependencies`: exit 1,
  OpenRouter requires an HTTPS_PROXY or ALL_PROXY proxy.

No proxy variables were found in the checked process/user/machine environments.
Awaiting the operator's container-reachable proxy address or local configuration
path. No live engine compatibility or provider extraction pass is claimed.

## 2026-10-30 — Proxy configured; live compatibility results

Operator supplied local proxy port 10808. Verified HTTP CONNECT from the host
and from a disposable local Python container: OpenRouter public models endpoint
returned HTTP 200, without an API key. Saved container-reachable HTTP_PROXY and
HTTPS_PROXY plus internal NO_PROXY exclusions in the ignored product .env;
provider credentials were preserved and never printed.

`uv run python deploy/product/run.py dependencies`: exit 0, infrastructure only.
Both product Hindsight and LiteLLM containers became healthy. Development
containers remain running; no development volumes were reset.

Added opt-in synthetic tests/integration/test_hindsight_store.py before adapter
implementation. Ordinary invocation skips; running API reports 1.1.0.

- Initial explicit live multipart experiment: 1 failed, HTTP 400 at async retain.
  Scratch-bank cleanup completed. Pinned source confirms deliberate rejection of
  duplicate document_id values on the queued path.
- With ENGINEERING_MEMORY_LIVE_STORE=1, `uv run pytest tests/integration/test_hindsight_store.py -q --tb=short -k single-item`:
  1 passed, 1 deselected in 19.13s. Actual extraction/recall through LiteLLM and
  OpenRouter succeeded; replay returned the same completed operation/time,
  provenance/time/tags round-tripped, unrelated strict scope returned nothing,
  and replacement removed old facts. Scratch-bank cleanup completed.
- `uv run pytest -q` before parameterizing that experiment: 1655 passed,
  5 skipped in 65.82s. Ruff lint passed, 325 files already formatted.

T004 is partially executed but remains unchecked because required multipart
semantics fail. No adapter or product E2E success is claimed. The external
configuration blocker is resolved; the remaining blocker is the verified engine
contract conflict. decision-needed.md proposes a concrete resolution requiring
human governance review under the approved plan.
