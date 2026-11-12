# Reflect evaluation on project history

## Scope and method

The comparison ran on 12 November 2026 through the engineering-memory MCP surface, using Hindsight 1.2.0 and GPT-OSS-20B through OpenRouter. The bank contained 17 Codex sessions from one project, covering 3–9 November 2026. The importer rejected the current session envelope format. For this evaluation, compatible text snapshots preserved session identity and dates and included user and assistant dialogue. The snapshots excluded tool calls and bookkeeping. The sessions were selected for the availability of evidence for the evaluation questions. No project models were loaded.

The eight questions and their 20 expected points were fixed before the run. Six questions covered decision synthesis or changes over time. Two controls asked for a specific fact. Each pair used the same question and project scope. Recall returned up to ten matches. The background worker was disabled during measurement. The bank counts were identical before and after both runs, with 17 documents, 584 nodes, and 247 observations.

A manual review counted a point when the returned evidence or synthesis stated it and the references included support from a source recorded in the case set. This rule can miss a correct point backed by a different source. Every returned reflect reference opened in the local archive and matched the requested project.

## Completion and latency

| Run | Recall completed | Reflect completed | Recall median | Reflect median |
| --- | ---: | ---: | ---: | ---: |
| Standard 30-second limit | 8/8 | 1/8 | 6.52 s | 23.27 s (one completed call) |
| Diagnostic run with a longer limit | 8/8 | 8/8 | 6.49 s | 37.86 s |

All six synthesis calls and one lookup control timed out under the standard limit. The diagnostic run used a 150-second Hindsight request limit and a 165-second MCP call limit. Recall returned the same ordered results for all eight questions in both runs. In the diagnostic run, recall ranged from 6.15 to 7.24 seconds and reflect from 30.05 to 63.21 seconds.

## Grounded coverage

| Question kind | Expected points | Recall | Reflect with longer limit |
| --- | ---: | ---: | ---: |
| Evolution | 9 | 6 | 6 |
| Decision synthesis | 9 | 4 | 7 |
| Direct lookup | 2 | 2 | 2 |
| **Total** | **20** | **12** | **15** |

One synthesis answer correctly connected access controls, archive validation, and protection against disclosure in logs across separate conversations. Other answers misstated a positive lookup as empty, attributed another task's checks to an engine upgrade, or described a pending real-export check as completed. Openable references allow these claims to be checked individually.

## Consumer routing

Use `search_memory` for a direct lookup or when the response must fit the standard request limit. Use `reflect` when the question needs evidence connected across conversations and the caller can allow the additional time. Check substantive claims against the referenced conversations with `get_conversation`. When reflect times out or returns insufficient evidence, use `search_memory` and inspect the underlying conversations.

This was one week of one project with a single model and one measured run per timeout configuration. The result estimates behavior for this setup. The [operator guide](reflect-evaluation.md) describes the repeatable procedure. [Tracking issue #31](https://github.com/nkz-soft/engineering-memory/issues/31)
