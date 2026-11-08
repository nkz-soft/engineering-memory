# Data Model

| Record | Fields and rules |
| --- | --- |
| Private case | Unique opaque ID, kind (`evolution`, `decision`, or `lookup`), project key, question, nonempty expected points and local source references. Freeze before calls. |
| Private case set | Version, engine and model profile, coarse corpus summary, project-model availability, and cases. The runner copies this profile to the local run. |
| Operation outcome | Operation, status (`completed`, `insufficient_evidence`, `failed`, or `unattempted`), elapsed milliseconds for attempted calls and local evidence or a safe failure category. A failure carries no answer. |
| Paired result | Case ID and two outcomes. A review records covered point IDs per operation, supported synthesis, unsupported claims, and chronology where applicable. |
| Run | Case-set version, date, engine and model profile, non-identifying corpus summary, fixed recall limit, per-case pairs and completion status. |
| Published comparison | Counts and aggregate coverage per operation and case kind, synthesis and unsupported-claim counts, median and range, failure counts, limits and routing rule. Excludes text and identifying references. |
