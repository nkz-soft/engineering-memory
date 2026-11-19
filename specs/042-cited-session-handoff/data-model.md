# Data model — Cited session handoff

| Entity | Data and invariants |
| --- | --- |
| Session selection | Required stable document ID and exact project. Use existing validation and check archived identity, provenance and project tag before reading evidence. An optional validated link origin belongs to presentation. |
| Evidence manifest | Request-local selector → canonical document, project, original message index/time and role, optional tool index, field and bounded sanitized text. Model selectors are opaque and valid only in their own request. |
| Handoff entry | Section from the fixed set of five, status from recorded/unknown/conflicting, one bounded plain-text paraphrase and zero to three selectors. Recorded and conflicting entries require supporting selectors. Conflicting entries require at least two distinct anchors. Unknowns may have no anchor when evidence is absent. |
| Handoff brief | Canonical session descriptor, ordered sections rendered from validated entries, explicit empty-section wording, and a notice for omitted evidence or entries. UTF-8 Markdown up to 8 KiB. |

The shared operation validates, reads, builds the manifest, optionally synthesizes and validates, then renders. Failure yields a fixed error and no partial response. Nothing persists. Viewer state belongs to the active unlocked session. It clears on lock or session change and ignores stale responses. A copy attempt leaves the displayed brief available until that state changes.
