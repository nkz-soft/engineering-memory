# Research: Live Hindsight Contract

## R1 — Reuse actual integration evidence

Decision: extend the existing suite and canonical engine service.
Rationale: `tests/integration/test_hindsight_store.py` already exercises explicit replacement, replay completion identity, all_strict filtering and mentioned_at. `test_bank_provisioning.py` demonstrates scratch-bank cleanup and missing config reads. CI currently runs ordinary pytest with no live opt-in. `deploy/hindsight/service.yaml` pins the engine by version and digest.
Alternatives: duplicate the engine deployment or rely on existing opt-in coverage; both leave unnecessary maintenance or gaps.

## R2 — Secret-free deterministic extraction

Decision: replace only the LLM dependency with a local schema-aware fixture service in CI.
Rationale: the behavior under test is actual engine persistence, queue retry identity, tags and time. Extraction request counters add evidence that operation replay does not repeat extraction. The fixture must reject unknown requests. Structured response details must be derived from the pinned engine during implementation and proven by a live run.
Alternatives: external paid credentials exclude forks; mocking retain/recall cannot verify engine behavior. This suite is not a model-quality evaluation.

## R3 — Temporal contract and tag vocabulary

Decision: test original dates and historically scoped retrieval, not generic chronological ranking; enumerate literal supported tag modes from the pinned schema.
Rationale: ARCHITECTURE §9 says temporal grounding. Existing code uses all_strict while §6 uses informal mode terminology. Import in reverse date order to distinguish original time from import time. Unknown/contradictory behavior is a failing contract finding, never silently skipped.
Alternatives: infer ordering from generic semantic recall or assume prose terms are literal mode names; neither is justified by local evidence.

## R4 — CI safety and observability

Decision: dedicated bounded live job, unique scratch banks, separate Compose project, unconditional teardown, no silent skips and synthetic-only diagnostics.
Rationale: ordinary offline checks must remain fast, and a passing skipped suite cannot gate upgrades. Use existing Python/httpx/pytest tooling and no new production dependency.
Alternatives: run against engineering-global or a developer service in CI; risks operator data and destroys isolation.

Research used repository source and a read-only research-agent review. No external API semantics have been asserted as verified. Product decisions are resolved; pinned-protocol details are explicit implementation validation steps.
