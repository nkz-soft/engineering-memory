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

## Import and model status

After unlocking the explorer, choose **Status** to check all four import
sources. The latest attempt and the last successful import are separate fields.
A failed attempt leaves the previous success visible. A clean scan clears old
errors, and skips or dry runs leave the success timestamp alone. **Waiting**
means the automatic importer observed deferred sessions. **No completed attempt
recorded** is expected before the first observed run, including after upgrading
an older state database. Reopen or reload the panel to read the latest
observations. They persist in the configured import-state database.

Enter a classified project slug to see the architecture, stack and decisions
models. **Stale** indicates an explicit stale signal from the model service
or a confirmed import for that project that began after the last refresh on
the same workstation. For remote endpoints, the view uses the service's
freshness signal. **Unknown** means the available evidence cannot establish
freshness. A failed refresh can appear
alongside the last successful refresh time. Status reads do not start imports
or model refreshes, and display only operational metadata.

## Search and evidence

Search and transcript reads work without synthesis configuration. If the explorer says Deep Recall needs synthesis configuration, set up the synthesis endpoint using the linked guide. If a source message has changed or is missing, the explorer marks the evidence as unavailable.

The listener is private to the workstation. Keep the printed key private and stop the process when finished.

## Archived coding sessions

Opening a Claude Code or Codex conversation shows normalized dialogue and tool
occurrences in archived order. Known recorded envelopes expose call identifiers,
requests, results and error metadata; unknown content remains literal text.
Calls and results may appear in separate messages/pages. A missing result on one
occurrence does not establish whether the call completed elsewhere.

Recorded patches and edit before/after text describe archived evidence, not the
current repository state. Original sanitized field text remains available.
Commands are inert: viewing never executes tools, applies changes, opens referenced
files or fetches external output. Non-text content is limited to archived markers.

Fields longer than 20 lines or 2,000 characters start with a preview. Use
“Show complete recorded request/result” to expand all archived text by mouse or
keyboard. This limits visible output, not archive reads or response sizes.

Each message and tool request/result has a link. Copy its link address to return
to that exact position, including beyond the first page. Opening a link after a
refresh requires the current access key; the link contains no credential or
quoted history. The target expands and receives focus. Browser back/forward
resolves the selected target again. The explorer must be running at the link's
origin; its port and key may change between launches.

These links select positions in the **current archived snapshot**. Re-import can
change those positions; links do not preserve old revisions. Existing verified
citations additionally check original timestamp and quoted source text and show
unavailable evidence if those checks fail. Invalid message/tool selectors are
reported as unavailable rather than silently selecting a nearby message.

## Prepare a session handoff

Open an archived session and select **Generate handoff**, then **Copy Markdown**.
Review the Markdown and paste it manually into the receiving session. If the
browser denies clipboard access, select and copy the text from the field.
Generation uses the configured [Deep Recall synthesis endpoint](deep-recall.md)
for bounded excerpts of the selected sanitized session. The brief marks missing,
conflicting or omitted evidence and links to the supporting archive fields.

From the CLI, pass the archived document ID and its project:

```text
engineering-memory session-handoff claude-code:SESSION_ID --project PROJECT
```

The CLI prints Markdown to stdout. Its citations use viewer fragments by
default. To make them clickable against a running explorer, pass
`--explorer-origin http://127.0.0.1:PORT` with the printed origin. Citations
address the current archived snapshot and require normal viewer access.
Neither generation nor copying launches, resumes, or sends a message to an
agent.
