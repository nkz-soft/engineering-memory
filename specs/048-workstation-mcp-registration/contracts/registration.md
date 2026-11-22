# Installer and Terminal Registration Contract

## Interactive flow

After the installed executable is available, show current-user clients and their resolved profiles. Offer selection per resolved profile, unchecked by default. Show a shared Codex target once with both client names. Explain unresolved or blocked targets and show a continue path when the user skips or no clients are found. Ask separately before replacing a same-name conflict. Deferring this step writes no client configuration. Silent Windows install does not enter it.

Windows uses bounded structured helper requests through the existing installer UI boundary. Scan returns stable client/target identities, safe display paths, states and an opaque snapshot identity. Apply accepts only the selected identities and replacement decisions from that scan and revalidates against current discovery. Arbitrary paths and commands from the UI are not accepted. Keep config bytes, provider keys, foreign commands and raw process output out of messages and logs. Ubuntu launcher and interactive `engineering-memory setup` use the same decisions and statuses.

## Persisted entry and verification

The single server key is `engineering-memory`. Its stdio launch is the absolute installed executable with one argument, `serve`. A new or replaced entry supplies no custom environment or working directory. Preserve the original entry on refusal or failed write. Do not start the command of a conflicting entry. Re-read the selected target and check exact launch semantics before running the local probe.

Show saved, already configured, declined, blocked or failed for persistence and passed, failed or skipped for the local probe, with a sanitized reason when relevant. A probe pass requires both named tools after MCP initialization and must appear as local verification. Display restart guidance for fresh-session confirmation. A known incompatible Codex CLI or managed/profile override receives its own diagnostic alongside those statuses.
