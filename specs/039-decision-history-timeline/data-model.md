# Data Model — Source-Backed Decision History

The result is transient. The normalized archive remains the evidence store.

| Concept | Fields and rules |
| --- | --- |
| Decision history | Project slug, requested topic, result status, dated and uncertain events, unresolved conflicts, coverage and uncertainty reasons. |
| Event | Kind (`proposal`, `adoption`, `revision`, `supersession`), version description, optional prior version for revisions and required prior version for supersession, optional documented reason, primary action citation and supplementary citations. Evidence for both versions and their relationship is required for a displayed supersession. |
| Chronology | `known`, `unknown` or `disputed`. Known dates come only from the primary action message. Unknown and disputed events carry a null ordering timestamp. A known event tied with another known event has an explicit ordering warning. |
| Unresolved conflict | Summary plus two or more distinct competing accounts, each with its own support. Accounts can discuss disputed evidence without being promoted to established lifecycle events. |
| Message anchor | Existing Deep Recall shape. Document ID, zero-based message index, field, optional tool index, original nullable message timestamp and verified quote. |

The model may select existing passage selectors and classify the evidence. The service derives the actual anchors and event ordering. A reply containing bad selectors, fabricated metadata, malformed records or incompatible links within the draft yields verification failure with no result content. Uncertain dates and incomplete retrieval can accompany valid evidence. Duplicate actions of the same kind on the same source message collapse to one event when their payloads agree. Incompatible duplicate event payloads fail verification. Put competing accounts in the conflict collection with separate evidence.

The action's kind is based on the cited action, so a later dissenting message leaves the earlier decision's outcome open. A sourced revision changes a version of the documented decision. A sourced supersession explicitly replaces an earlier version. A supersession requires evidence linking the two versions of the requested decision.
