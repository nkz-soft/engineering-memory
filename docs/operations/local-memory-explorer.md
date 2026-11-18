# Local memory explorer

Open an existing imported corpus from a browser on the same workstation. Use the same active profile and backend configuration as the CLI and MCP server. See [workstation setup](workstation-install.md) for the initial import and [Deep Recall](deep-recall.md) for synthesis configuration.

```sh
engineering-memory explore
```

Open the printed loopback URL and enter the access key from the terminal. Each launch uses a new key and a dynamically selected port. The browser keeps the key in page memory. Reloading the page requires entering it again. Select **Lock** to clear the current view, or stop the command with Ctrl+C to end access.

1. Enter a project slug as it appears in the import classification.
2. Enter search terms and choose **Search**. Open a result to see its sanitized conversation, original time and source. Use **Next messages** to read further.
3. Enter a cross-session question and choose **Deep Recall**. Open a citation to inspect the exact archived message and highlighted quote. Expand **Coverage limitations** when an answer is partial.

4. Enter a decision topic and choose **Decision history**. The timeline links proposals, adoptions, revisions and replacements to their archived messages. It flags uncertain dates and unresolved conflicts. Decision history uses the same synthesis configuration as Deep Recall.

Search and transcript reads work without synthesis configuration. If the explorer says Deep Recall needs synthesis configuration, set up the synthesis endpoint using the linked guide. If a source message has changed or is missing, the explorer marks the evidence as unavailable.

The listener is private to the workstation. Keep the printed key private and stop the process when finished.
