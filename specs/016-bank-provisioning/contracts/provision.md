# Operator Contract: Provision

Proposed command after Phase 2 implementation:

```text
engineering-memory provision
```

- Reads existing ENGINEERING_MEMORY_ settings and the packaged mission; default bank is engineering-global.
- Creates/configures the bank explicitly and verifies exact mission read-back.
- Exit 0: verified success. Nonzero: invalid settings, unavailable/unauthorized engine, invalid response, timeout or mission mismatch.
- Output is a short safe status; no token, authorization header, conversation or raw response body.
- No input conversation, arbitrary mission option, delete, reset, re-extract or consumer MCP tool.
- Repeated invocation converges without new memory items or unrelated configuration changes.
- Overall default operation deadline 60 seconds; individual requests at most 30 seconds and bounded by remaining time.

## Engine boundary

Only memory/hindsight knows the bank/config routes. Confirm pinned GET/PATCH schema before implementation; expected mission update is narrowly scoped to retain_mission (with the envelope required by the pin). Create through a config write if supported, otherwise use the dedicated bank creation route. Never call memories/retain for creation. Preserve reflection mission and unrelated settings. A mismatched read-back is failure even after an HTTP success.

## Policy evolution

Edit the version-controlled mission alongside Architecture §12, verify equality tests and rerun provision. Future extractions use the new policy. Existing memories require the separate archive replay procedure; provision never initiates it.
