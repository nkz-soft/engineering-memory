# Local neighborhood contract

## Authenticated operations

- `POST /api/neighborhood` takes a classified project and exactly one root: a canonical document ID, or a validated project-relative path plus the scoped repository selection. Reuse the explorer's exact project validation and transport protections. Any user-visible error uses a fixed category.
- Return the root label and up to 30 direct typed edges with endpoint labels and opaque, generation-bound evidence handles. Include generation coverage and truncation state. The server owns limits. Use a deterministic order by recorded time and stable edge identity and one extra row, or an equivalent bounded query, to determine truncation.
- `POST /api/neighborhood/evidence` takes project and edge handle. Resolve the indexed locator in that scope. Load and validate the current sanitized archive record against the guard, then return the type, context and bounded literal evidence with an exact viewer selector. If the record, project, selector or snapshot no longer matches, return a fixed unavailable state. An expired generation requires a graph reload.
- The viewer validates the optional graph snapshot selector with the paged normalized-record read before rendering or focusing the target. Include only bounded stable identifiers, positions and the snapshot guard in the fragment. Requests without this guard keep the existing viewer behavior. No transcript text appears in the URL.
- Keep distinct UI states for index absent, ready-empty, limited, partial and unavailable evidence. Empty or stale results never block normal session reads. Switching roots or locking clears selection and aborts or ignores old responses.

## Browser interactions

Open the graph from the session viewer or by entering an exact file path within a selected project/repository. Render the root and one-hop neighbors with keyboard-operable controls for edges. Selecting an edge exposes the relation type and evidence in a readable detail area. A session or file can become the new root. PR and commit labels are terminal nodes. Links to evidence stay on the existing local explorer origin.

## Local refresh

Proposed operator command `engineering-memory rebuild-neighborhood`. Read the configured sanitized archive through its interface. Replace the derived generation only following a completed build. Report aggregate counts and completion/failure via the CLI. Do not print source contents. Concurrent refreshes must serialize or safely refuse the later invocation.
