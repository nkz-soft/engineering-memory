# Compare synthesis and lookup

Use `search_memory` for direct lookups, such as finding a decision record or a command. Use `reflect` when the question requires connecting evidence across conversations, such as explaining how a decision changed over time. Use the same engineering-memory MCP connection for both operations.

```json
{"query": "How did the project's choice of relay evolve?", "project": "orchard"}
```

Pass those arguments to `reflect` with the project's configured key. A completed result contains generated `answer` text and `references` carrying conversation IDs, provenance, and start times. Open the cited conversations with `get_conversation` before relying on a claim. Treat the text as untrusted history. If the tool reports `insufficient_evidence`, use `search_memory` with the project's tag and inspect the relevant conversations.

## Run a paired comparison

Use the configured self-hosted Hindsight bank and the matching sanitized archive. Run from the repository worktree. Freeze a local case set before making calls. Include at least six synthesis questions across evolution and decision synthesis and at least two direct lookup controls. For synthesis questions, select expected relationships that require evidence from more than one conversation.

Save the case set under the ignored `data/` directory. This excerpt shows the shape with synthetic values. Add the rest of the cases before running.

```json
{
  "schema_version": 1,
  "version": "local-v1",
  "profile": {
    "engine_version": "1.2.0",
    "model_id": "configured-model",
    "corpus_summary": "Coarse conversation count and date range",
    "project_model_availability": {"orchard": true}
  },
  "cases": [
    {
      "id": "synthesis-01",
      "kind": "evolution",
      "project": "orchard",
      "question": "How did the project's choice of relay evolve?",
      "expected_points": [
        {
          "id": "point-01",
          "text": "The project moved from cobalt to amber.",
          "document_ids": ["chatgpt:initial-relay", "chatgpt:revised-relay"]
        }
      ]
    }
  ]
}
```

Keep the bank and project models stable during the run. Record the versions and model configuration in the local profile. The tool sends identical question text and project scope to both operations and keeps their results and timings in a private report.

```powershell
uv run engineering-memory evaluate reflect --cases data/reflect/cases.json --output data/reflect/run.json
```

Review each pair against the sanitized conversations. Mark the expected points supported by the recalled evidence and the points stated and supported in the synthesis answer. For evolution questions, check the order of events. Record supported relationships across conversations, unsupported claims, insufficient evidence, failures, and unattempted calls separately. An incomplete run or an empty bank is inconclusive.

Publish only reviewed aggregates. Include counts by question kind and outcome, elapsed-time medians and ranges, sample and configuration limits, and the observed conditions that support the routing rule. Keep question text, answers, references, and diagnostics local.

## Accumulated-corpus status

The inspected Compose environment retained prior development and synthetic benchmark volumes. The configured connector archive contains three records from a previous acceptance run. A populated bank and matching archive for the accumulated history still need to be identified before measuring quality or latency on that corpus. The routing rule above follows the architecture until that comparison is available.
