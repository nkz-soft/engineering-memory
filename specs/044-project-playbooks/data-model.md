# Playbook Data Model

## Identity and content

| Record | Fields and invariants |
| --- | --- |
| Playbook | Composite key `(project, id)` with an exact classified project slug and operator-chosen playbook slug. Both are bounded to 200 characters and use the existing project slug convention. |
| Pending draft | At most one per key. Contains a fresh opaque revision token, sanitized title, ordered steps and ordered example references. Staging replaces only the pending draft. |
| Approved version | Key `(project, id, version)`, positive contiguous version starting at 1, unique approval revision per playbook, UTC approval time and immutable copy of the reviewed sanitized content and references. |
| Example reference | Stable `document_id`, exact project, original UTC conversation time and snapshot hash matching the existing neighborhood guard. Input IDs are unique within a draft and retain submission order. |

Titles and steps must remain nonblank after sanitization. Titles are at most 200 characters, each step at most 2,000 characters, with 1–50 steps and 1–10 examples. Apply input bounds before parsing or redaction and validate the stored representation after redaction. Reject unsafe terminal control characters in stored text. The catalog holds no conversation payload.

## Write and read semantics

- Local writer initializes the versioned schema. Use indexed keys for project/ID lists and version lookup. Use an SQLite transaction with write serialization for approval. Read surfaces use read-only connections and never initialize or migrate the catalog.
- Upon approval, an already approved revision returns that version without modifying any pending draft. Otherwise, verify the pending token and its archive references, allocate the next number, insert the approved version and clear the matching draft as a unit. Failures roll back the catalog mutation. Source validation and archive navigation use the snapshot guard because the archive and catalog are independent boundaries.
- Readers consult only approved versions. List latest versions ordered by ID within one project and use an exclusive cursor. A direct lookup defaults to latest and accepts an explicit approved version.
- Keep catalog data in `playbooks.sqlite3` under the configured archive root. Back it up with the archive using a consistent SQLite backup. Archive replay cannot reconstruct manual approvals.
