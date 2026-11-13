# Deep Recall data model

All run data is request-local and discarded after the response.

| Entity | Fields and rules |
| --- | --- |
| Request | `query`, `project`: strict strings. Question is nonblank and at most 2,000 characters. Project follows existing classified project tag validation. No caller-supplied filters or budget overrides. |
| Candidate | Document ID, exact project and indexed provenance, best rank. Merge matching IDs; quarantine conflicting provenance. No recall snippet crosses into synthesis. |
| Manifest entry | Opaque per-request selector mapped to document ID, zero-based message index, field (message text, tool request, tool result), optional tool index, archive time and sanitized excerpt. Only nonempty, in-scope slices admitted. |
| Timeline entry | Bounded paraphrase and one or more verified anchors; order by earliest cited message time, unknown times last, with stable document/index tie breakers. |
| Anchor | Document ID, message index, field, optional tool index, archive timestamp, and archive-derived quote. |
| Coverage | Counts for searches, candidates, archive loads, pages, passages, evidence bytes, skipped records by safe reason, and a list of encountered limits. Unknown total corpus size is not reported as complete coverage. |
| Result | Exact project, status, timeline, coverage and safe uncertainty codes. `partial` requires supported entries and a gap. `insufficient_evidence` and `verification_failed` have an empty timeline. |
