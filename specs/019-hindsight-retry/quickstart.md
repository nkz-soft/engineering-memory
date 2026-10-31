# Validation guide: Hindsight retries

Run from the issue worktree after implementation. Requires Python 3.13 and uv. Offline tests use synthetic fixtures/mock transport, with no live engine or credentials.

```powershell
uv sync --locked --group dev
uv run pytest tests/unit/test_hindsight_retry.py tests/unit/test_hindsight_store.py -q
uv run pytest tests/contracts/test_hindsight_store_passes_the_contract.py tests/integration/test_hindsight_store.py -q
uv run pytest tests/integration/test_pipeline_from_fakes.py tests/structure -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Expected: targeted tests and offline regressions pass; existing gated live tests may skip. Report actual counts and skip reasons. Ruff/whitespace checks exit zero. The retry test file is planned, not present during planning.

For each implementation increment, record failing tests before code and passing tests afterward. Prove every contract row: transient status/timeout/reset recovery; permanent failures and malformed successful responses make one request; persistent 503 stops at four attempts; deadline prevents later sleeps/requests; repeated submissions preserve identical bytes; poll recovery never resubmits retain; recall keeps scope.

Inject clock, sleep and randomness to avoid real waits; assert growing pre-cap floors and valid jitter bounds. Exercise owned async cancellation and injected sync transport. Capture attempt/success/exhaustion events with synthetic canaries in bodies, queries, headers, responses and exception messages; none may escape. Preserve pending identity and pipeline failure-isolation regressions.

Optional live tests remain separate evidence of engine idempotency; mock tests alone cannot prove billing or actual extraction deduplication.
