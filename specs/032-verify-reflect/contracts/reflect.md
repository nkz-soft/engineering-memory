# Reflect Contracts

## Consumer MCP operation

`reflect` takes a nonblank `query` and an explicit `project` in the same form as existing project-scoped access operations. It returns an `answer` and deduplicated `references` in the existing consumer citation form, or `insufficient_evidence` with an empty reference list and no answer. Reuse existing access error mapping for invalid input and dependency failures. Verify each reference against sanitized archive provenance and the requested project. Withhold the answer if any evidence is explicitly attributed to another project. Treat the generated answer as untrusted and require consumers to check citations for consequential claims.

## Engine-neutral boundary

Add `ReflectionReader.reflect(query: str, tags: tuple[AnyTag, ...]) -> ReflectionResult` with generated text and candidate provenance. Require the adapter to apply strict project tag matching. Keep the existing `MemoryStore` protocol stable. Map engine failures to existing read boundary exceptions. Only the adapter sees backend response fields.

## Evaluation command

`engineering-memory evaluate reflect --cases PATH --output PATH` reads the local case set and writes the local paired run with the existing atomic report-writing pattern. Require both paths to resolve under the ignored local `data/` directory before making any calls. Use the configured stdio access process. Validate the case-set profile, case IDs, scopes, and expectations before any calls. Record both outcomes for each case, including when one call fails. If the session fails permanently, record the unattempted operations and mark the run incomplete. Exit unsuccessfully on invalid input, output failure, or a run containing operation errors. Preserve the report for review when the run reaches the output step.
