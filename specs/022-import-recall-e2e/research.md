# Research: Import and recall end to end

## R1 — Coverage gap
Decision: Add explicit live end-to-end coverage and required CI selection.
Rationale: tests/integration/test_operator_cli.py::test_live_commands imports and recalls a substring but omits full provenance/tags/time checks. deploy/hindsight/contract.py selects only the engine contract suite. Neither closes #23 alone.
Alternatives considered: retain 200 checks and fake-only integration cannot establish recallability.

## R2 — Reproducible engine lifecycle
Decision: Use testcontainers-python with the image digest already pinned in deploy/hindsight/compose.contract.yaml and the existing tests/integration/hindsight_contract/llm.py extraction fixture. Use disposable network, storage and dynamic ports.
Rationale: The stack mandates testcontainers; the existing fixture gives credential-free deterministic extraction while real Hindsight executes retain, extraction processing and recall.
Alternatives considered: external LLM introduces cost, secrets and nondeterminism; Compose remains the separate existing contract gate.

## R3 — Evidence without a domain contract change
Decision: Recall through HindsightStore and supplement with raw integration-only engine evidence.
Rationale: memory/interface/store.py exposes RecallResult(content, provenance, score). Provenance has imported_at, not original time or tags. Raw fact mentioned_at and engineering_memory.started_at metadata must both match historical fixture time; complete raw tags must equal expected tags. Adapter filtering alone cannot prove the complete persisted tag set.
Alternatives considered: expanding RecallResult only for a test is unnecessary scope.

## R4 — Sensitivity and safety
Decision: Independently specified expected fields, omission controls, and a real wire-timestamp omission run on an isolated bank.
Rationale: Mirroring serializer output as the expected result hides serializer bugs. Timestamp metadata surviving cannot prove temporal grounding survived.
Alternatives considered: unbounded waits, shared production bank or real histories are unacceptable for repeatable CI.

## Clarification review
No critical ambiguity remains. Scope, actors, entities, failure handling, privacy, external dependencies, completion signals and terminology are covered. Concrete dependency API selection is an implementation detail, not a product decision. No extension hooks file is present. Findings come from current repository code, not assumptions about an unverified upstream release.
