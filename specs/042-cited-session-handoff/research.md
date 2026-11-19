# Research — Cited session handoff

## Scope and evidence

**Decision** — Load the explicitly selected session directly through the archive interface. Reuse the validation conventions in `access/service.py` and the bounded evidence approach in `access/deep_recall.py`.

**Rationale** — #88 specifies a selected archive session. #82 provides synthesis infrastructure, and feature 040 already documents anchor navigation. Search ranking and Hindsight snippets add evidence sources the operator did not select.

**Alternatives** — Running Deep Recall with a handoff prompt would depend on indexing and could pick unrelated sessions. A transcript dump would preserve original wording but force the recipient to reconstruct decisions and checks.

## Generation and confidence

**Decision** — Extend the configured optional synthesis adapter with a specific handoff prompt and closed schema. Use prompt-local selectors for anchors. Require recorded evidence for confirmed items, use attributed or unknown status for gaps, and derive links, labels and timestamps from trusted application data. Treat selected passages as untrusted, inert data. A nonempty archive with no configured adapter produces a configuration error. An empty manifest can return insufficient evidence without an adapter call.

**Rationale** — A deterministic excerpt is reproducible but cannot reliably identify adoption, changes and unanswered questions across existing normalized source shapes. Structured synthesis can group sparse evidence, while validated selectors and escaped output make each result inspectable. A valid position alone cannot prove a paraphrase. Tests and manual inspection must exercise semantic correctness.

**Alternative** — A new independently configured agent or model client creates an unnecessary execution or delivery path. Reuse the existing HTTP adapter's timeout, byte cap and credential handling.

## Links and copy

**Decision** — Generate links using the existing feature 040 selector. The viewer uses its authenticated loopback origin. The CLI emits fragment-only links by default and accepts a validated optional loopback origin. Render literal Markdown in the viewer and copy it only on explicit action.

**Rationale** — CLI generation is independent of viewer lifetime. Viewer links remain usable in a running instance, subject to authentication. Using one renderer prevents divergence in headings, citations and omission notices.

**Alternatives** — Persisting copied briefs or adding an agent dispatch button expands the issue's scope. Launching a viewer from the CLI would create a process and couple an otherwise read-only command to port state.
