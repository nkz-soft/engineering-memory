# Validation quickstart

Use a temporary local archive and SQLite store, a dedicated inbox and synthesized exports. Provision the standard test memory store before testing real imports.

1. Put a valid ChatGPT fixture into the inbox. Set `ENGINEERING_MEMORY_CHATGPT_EXPORT_INBOX` to that directory. Schedule `engineering-memory acquire-chatgpt --json` with a local scheduler and capture its exit status and safe output. After two unchanged observations, expect one completed acquisition without manual import. Compare the archived ZIP bytes with the fixture. Rename a copy and confirm no additional import.
2. Add a stable truncated fixture. Confirm the scheduled command exits 1, does not call ingestion and leaves `engineering-memory status --json` unchanged. Move that file out of the inbox. Repeat with a corrupt late member and a valid ZIP with a malformed conversation-array tail.
3. Simulate a failed import after acquisition. Remove the inbox copy and run the next check. Confirm the same archived ZIP is used, previously successful conversation work is skipped, and the acquisition becomes complete only after a successful report.
4. Run `engineering-memory acquire-chatgpt --file PATH --json` with a valid fixture carrying known production evidence. Check text and JSON status for that time and its evidence, independently of completion time. Repeat with unavailable evidence and expect unknown. Check existing status and dry-run against an unmodified v1 database.
5. Verify the private local download from an actual account without committing it or placing its contents in logs or issues. Record only which evidence category was available. Complete the existing live import/recall checks through the standard integration setup.
