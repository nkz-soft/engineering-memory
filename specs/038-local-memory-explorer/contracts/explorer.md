# Contract: Local Memory Explorer

`engineering-memory explore` starts in the foreground at `127.0.0.1` on a dynamically selected port and prints the URL and a per-launch credential separately. An authenticated browser session ends when the process exits. The operator opens the address and enters the credential.

| Method and path | Request | Response |
| --- | --- | --- |
| GET / | Exact launcher Host | Page shell and links to bundled assets. |
| POST /api/search | JSON `query` and bare `project` | Unchanged `search_memory(query=query, tags=[project_tag])` response. |
| POST /api/deep-recall | JSON `query` and bare `project` | Unchanged `deep_recall(query=query, project=project)` response. |
| POST /api/conversation | JSON `document_id`, `offset`, `page_size` | Unchanged `get_conversation` response. |

The browser sends the bearer credential and exact origin on each data request. Reject a foreign or missing Origin, a wrong Host, missing authentication and non-JSON data requests before dispatch. Disable automatic API docs, use no-store for data responses and serve a same-origin content security policy. The browser treats corpus content as text.

Error bodies contain a fixed error code. Use 400 for invalid input, 401 for missing or incorrect credentials, 403 for rejected origin or host, 404 for missing records, 503 for unavailable resources or optional synthesis, and 500 for corrupt, rejected or internal reads. Return Deep Recall answer statuses in its successful result envelope. The view renders `completed`, `partial`, `insufficient_evidence` and `verification_failed` distinctly.

For a citation, request a page with offset equal to `message_index`. Resolve field `text`, `tool_request` or `tool_result` against the first message and the specified tool index. Check that the field contains the quote using the same whitespace normalization as Deep Recall. If the field or quote is missing, show unavailable evidence. Continue conversation paging using `next_offset`.
