# Verification: issue #20

## Test-first evidence

- Initial new retry tests plus updated dependency assertion: 15 failed, 13 passed before implementation. Failures showed missing transient recovery, exhausted retry counts, safe events and Tenacity dependency.
- Policy validation increment: seven expected failures (DID NOT RAISE ValueError), then passing after validation.
- Correlation increment: expected missing operation_id failure, then passing after retain/poll correlation fields.
- Independent review found uncertain acknowledgement followed by permanent rejection could discard identity within one retry sequence. Added a regression first: failed with two UUIDs. After preserving uncertainty across attempts, the same regression passed with byte-identical payloads.

## Final commands and results

- `uv run pytest -q`: 1831 passed, 27 skipped in 101.59s. This full run started before the final correlation/deadline/review regression additions; the affected adapter tests were rerun afterward as below.
- `uv run pytest tests/unit/test_hindsight_retry.py tests/unit/test_hindsight_store.py -q`: 77 passed in 1.79s after the identity fix and final test additions, with no warnings.
- `uv run ruff check .`: All checks passed.
- `uv run ruff format --check .`: 386 files already formatted.
- `git diff --check`: exit 0.

The skips come from existing opt-in live tests and contract/environment cases that are not applicable to the selected implementation. No live extraction/billing experiment was run; offline tests verify byte/identity reuse, not engine billing behavior. Windows sandbox socket restrictions stalled asyncio loop initialization; owned-client and full-suite verification ran outside the sandbox and passed.

## Review

Independent code review completed, then re-reviewed the identity fix. No remaining critical or important findings. Existing public memory interface, archive order, sanitization, tags, provenance and pending replay rules remain unchanged. Tenacity implements the existing ADR-004 Retry choice. Version 9.2.1 uses the supported multiplier argument; dependency minimum reflects that API.
