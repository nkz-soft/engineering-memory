# Deep Recall

Use Deep Recall to reconstruct how a decision changed across imported sessions in one project. Provide the exact classified project value used during import.

```powershell
engineering-memory deep-recall "Why did we change the cache policy?" --project demo --json
```

An MCP consumer connected to `engineering-memory serve` can call `deep_recall` with `{"query":"Why did we change the cache policy?","project":"demo"}`.

## Configure synthesis

Set `ENGINEERING_MEMORY_DEEP_RECALL__BASE_URL` to an OpenAI-compatible API base URL such as `https://your-endpoint.example/v1` and `ENGINEERING_MEMORY_DEEP_RECALL__MODEL` to its model ID. Set `ENGINEERING_MEMORY_DEEP_RECALL__API_KEY` if the endpoint requires authentication. The endpoint must support a JSON object response from `POST /chat/completions`. The command and the stdio server read settings from their own environment and the standard configuration file. Keep credentials in environment variables or your secret store.

Deep Recall sends the question and selected sanitized passages from the requested project, with their timestamps, to that endpoint. Choose an endpoint approved for your history. Without this configuration, Deep Recall reports `unavailable`.

## Read the result

- `completed` has verified citation anchors and no observed coverage gaps.
- `partial` has verified citation anchors and reports gaps or limits.
- `insufficient_evidence` means the run established no supported entries in the history it examined.
- `verification_failed` means the synthesis could not be validated. The draft is discarded.

Use a citation's `document_id` and zero-based `message_index` as the document and offset for `get_conversation`. A tool citation also identifies the activity index and field. Quotes are checked against the cited sanitized passage. Read the surrounding context to assess the model's interpretation.

Coverage describes the searches, archive records and evidence the run examined. Search limits and missing evidence can leave relevant sessions out of a timeline. A missing message timestamp appears as unknown. Message offsets refer to the current normalized record and can change if that record is reimported with changed content.
