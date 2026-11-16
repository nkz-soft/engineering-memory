# Research: Local Memory Explorer

## Proposed architecture decision

**Context.** A browser needs an HTTP origin. The constitution requires a decision record and authentication before memory is made available over a port. The existing CLI already obtains the shared read service via `make_read_access`. The HTTP adapter will use that same service and the existing validators.

**Decision.** Start an explicit, foreground FastAPI listener on IPv4 loopback. Generate a high-entropy bearer credential for each launch and display it once in the operator terminal for manual entry. Keep it in browser page memory. Validate the exact Host and Origin on data calls, decline CORS, prevent framing and disable HTTP access logging. Keep read bodies, results and credentials out of URLs and persisted browser state. Bind to loopback with no host override. Write the architecture decision and any needed constitution clarification in the implementation PR.

**Alternatives.** An HTTP bridge spawning an MCP child preserves literal stdio routing but adds another process and lifecycle to achieve the same service behavior. A standalone web frontend configured against an engine would bypass access validation. A JavaScript build stack would add packaging and toolchain overhead for a single view. Bundled platform HTML, CSS and JavaScript fit the launch model and existing Python packaging.

**Consequences.** Reloading the page requires re-entry of the credential. Search can run without synthesis configured. This issue delivers browser exploration through scoped retrieval, with later roadmap issues covering timeline and dedicated archive browsing features.
