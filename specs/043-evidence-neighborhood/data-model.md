# Data model: Evidence-backed session neighborhood

| Entity | Identity and validation |
| --- | --- |
| Session node | Exact canonical document ID in a classified project. Use same-project resolution for continuation targets. |
| File node | Exact project, verified repository scope and normalized repository-relative path. Preserve case. Normalize separator aliases only where the tool/path form makes that interpretation unambiguous. Reject traversal, uncertain roots and redacted identities. |
| Commit node | Project, repository and verified object identity from recorded successful output. An abbreviation can be expanded only against unambiguous recorded identity in that scope. |
| PR node | Project and explicitly qualified host, owner, repository and PR number. Preserve a display label without dereferencing the destination. |
| Edge | Scoped directed endpoint identities, one relation type, and a selected evidence locator. Deduplicate identical typed endpoint pairs and prefer the latest qualifying recorded event with a stable locator tie-breaker. |
| Evidence locator | Document ID, normalized snapshot guard, original message index, optional tool index and field. The evidence may also have corroborating locators for a tool request/result pair. Store selectors and event time, with no excerpts. |
| Index generation | Schema/projection version, completion time, coverage counts, source snapshot lookup and adjacency entries. Counts distinguish skipped records from empty results. |

Use normalized provenance and an exact project tag together. A missing repository is acceptable for a file only when recorded context and configured checkout mapping establish one unambiguous repository and root. No lookups of live checkout files are needed.

Refresh builds a candidate generation while readers use the last published generation. Publish atomically in SQLite after a full pass. A terminal enumeration failure aborts publication. Failed refresh leaves the previous generation readable. The rebuild skips individually invalid/unavailable records with bounded diagnostics and exposes partial coverage. If archive content changes after indexing, the next evidence read checks the current document ID, project, repository, workspace context where used and snapshot. The normalized content hash covers messages, so validate provenance and scope separately. A mismatch surfaces unavailable evidence until refresh. Readers never mix index generations in one operation.
