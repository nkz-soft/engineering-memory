# Research decisions — Recall evaluation

## R1 — Score recall through the MCP consumer surface

**Decision.** Use the MCP SDK to call `search_memory` over stdio and score returned text in memory. Use the same source IDs as the archive and importer, and record a limit of ten and a single project tag.

**Rationale.** This measures the retrieval path that Hermes and coding agents use and exercises provenance enforcement. The existing pattern is in `tests/integration/test_access_mcp.py`.

**Alternatives considered.** Direct engine calls would measure a different boundary and conflict with Principle IV. Manual spot checks lack fixed inputs and category-level comparison.

## R2 — Use a synthetic corpus and deterministic topic matching

**Decision.** Pair authored conversations with questions, topic IDs, literal wording variants, and supporting document IDs. Use Unicode normalization and token-sequence matching. Average question scores equally.

**Rationale.** The inputs and published results are safe to share, the metric is reproducible on identical evidence, and each miss can be inspected through the topic ID. Use specific, discriminating aliases and avoid putting answer wording into the questions. Calibrate against the synthetic source material before the live comparison.

**Alternatives considered.** A private corpus prevents public reproduction. A model judge adds another model and another source of variance. Document-ID-only matching would give credit for unrelated facts from the same conversation.

**Limit.** Literal matching can miss paraphrases and can count a negated claim that repeats a topic phrase. The score measures topic coverage in retrieved evidence. Keep the benchmark and score versions fixed across a comparison.

## R3 — Change extraction in a separate live experiment

**Decision.** Import identical inputs into disposable self-hosted deployments. Provision each once before import, using the canonical mission for baseline and a recorded restrictive synthetic mission for the candidate. Reuse the existing provisioner and vary its packaged mission text only in a disposable source copy used for the candidate setup.

**Rationale.** A mission change after import cannot isolate extraction effects. Fresh engine and import state avoid stale facts and content-hash skips. Keep the same pinned engine, extractor, corpus, and retrieval settings. The existing fixture-model tests can validate wiring, while the live comparison requires an extractor that responds to the mission.

**Alternatives considered.** Reusing the active bank risks cross-contamination. Changing engine and mission together obscures attribution. Permanent support for an arbitrary mission override expands the production CLI beyond the benchmark.
