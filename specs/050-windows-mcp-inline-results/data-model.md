# Data Model: Windows MCP Wizard

| State | Fields and lifetime |
| --- | --- |
| Discovered row | Configuration path, client group, scan state, review token and safe diagnostic. One record per row from a fully valid scan. |
| Profile key | Case-insensitive normalized absolute Windows configuration path and exact client group. Require a unique match in both scans. A row without a path has no reusable key. |
| Attempt | Copied profile key, label, scan state, review token, safe diagnostic and per-attempt keep/replace decision. Create before prompting or showing progress. Discard at the end of the pass. |
| Outcome | Registration disposition, local check disposition, safe detail and review context. Keep the latest attempt for a profile during the wizard session. |
| Batch state | Idle or running. While running, ignore MCP page activation reloads and disable check/rescan/navigation controls that could start or change the pass. Restore the state even on failure. |

On first entry, scan and show actionable rows unchecked. On rescan, reconcile only unique profile keys. Preserve the last outcome as a previous result for the same profile, with the current scan state shown separately. Keep a pending selection only when the review token also matches. On a failed scan, keep prior outcomes visible and disable new apply attempts until a successful scan. Drop consent after every attempt or cancelled batch.

Completed rows can be unchecked after their attempt. To retry, rescan and select the intended profile again. An unresolved or changed profile never inherits replacement consent. A successful save may change the token and move the next scan to matching, so retry can verify without rewriting. Stale or malformed apply results do not prove a write or a probe succeeded.
