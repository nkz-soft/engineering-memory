# Windows Wizard Contract

On **Connect MCP clients**, display the discovered client group, proposed action or current scan state, registration outcome, and local MCP check outcome. Focus shows the profile diagnostic and any returned restart or client-specific guidance. An unchecked row is skipped and receives no apply request. A non-actionable row remains unavailable for selection.

**Check selected clients** requires an actionable selection. Complete the pass on the same page. A declined conflict displays **Kept** and **Skipped** and produces no apply request. A valid helper reply displays both outcomes, including **Saved** with a failed check where applicable. A stale target displays the safe rescan diagnostic. A failed or malformed helper exchange displays a setup failure with check **Unavailable**.

**Rescan** refreshes discovery and requires fresh review when a configuration changed. **Next** or maintenance **Apply** leaves the page without an implicit client run. Show inline guidance that a pending selection is only applied by **Check selected clients**. Maintenance checks and onward navigation retain the applicable settings confirmation and save requirements. Routine results are inline. Explicit write consent dialogs remain available.

Keep the existing `EM-MCP1` protocol, per-profile probe and installer user/integrity guards. Apply only the bounded set of known registration and probe statuses. Scrub malformed or unexpected subprocess output by showing a fixed diagnostic and failing only that row.
