# Research — ChatGPT export acquisition

## R1. Local inbox and scheduled checks

**Decision** Use the local directory option in issue #40. Run a one-shot command with Windows Task Scheduler or a Unix user scheduler. Download via the supported, signed-in flow into a dedicated inbox. Confirm that a file's identity, size and modification time agree on consecutive checks before opening it. Verify those properties again around staging. Ignore known partial download suffixes and all non-ZIP names.

**Rationale** The signed-in download is part of the supported OpenAI flow. A folder handoff keeps credentials out of this application and supports an offline acquisition contract. It automates validation, archival, import and reporting after the download. [OpenAI export guide](https://help.openai.com/en/articles/7260999-exporting-your-chatgpt-history-and-data)

**Alternatives** Mailbox delivery alone does not establish that the signed-in download can be completed. Logged-in browser automation against internal endpoints introduces credential handling and completeness risks rejected by the issue and ADR-006. Putting discovery inside `import` couples it to parsing and breaks the explicit-input contract. Manual placement alone remains the fallback but does not trigger an unattended refresh.

## R2. Preflight before ingestion

**Decision** Stream from an isolated snapshot. Check ZIP layout, CRC and bounded expansion for all regular members. Check for duplicate member names and ambiguous numeric split indices, and use the existing streaming scanner to finish every selected conversation array before ingestion. Keep individual conversation semantics with the existing parser. Verify the zero-based contiguous split layout against the repository fixtures and the available local export before finalizing the strict rule.

**Rationale** The existing scanner yields before EOF. Valid early records, a correct central directory and a quiet download are individually insufficient to prevent a later truncation from reaching the pipeline. For supported split archives, a missing internal part can be detected. No archive inspection can establish that ChatGPT included every conversation or every final split part without an authoritative manifest. ADR-006's no-deletion rule remains necessary.

## R3. Durable publication and restart

**Decision** Use content-addressed ZIP storage and a separate SQLite ledger. Serialize scheduled and explicit acquisition invocations with the same local lock. Use the importer report as the completion decision and existing conversation state to skip successful deliveries after interruption.

**Rationale** A private metadata intent is durable before the blob is published. The ZIP still precedes the ledger. If the process stops between publication and ledger insertion, the next run verifies the published bytes and records them using the intent, even if the original file is gone. The ledger stores metadata only, keeping the PostgreSQL and object storage paths open. Older snapshots can revert changed conversations, so the coordinator should reject older dates when timestamps are comparable.

## R4. Export production time

**Decision** Treat export-level timestamp evidence with an explicit offset as authoritative only if its field and meaning can be validated. Otherwise, use the latest consistent modification time of conversation ZIP members as an estimate when the timestamp has a known offset, or when the operator explicitly configured an offset for the export's ZIP wall-clock times. Record the evidence type. Missing, implausible or ambiguous evidence becomes unknown.

**Rationale** The public export guide documents ZIP delivery and expiration but gives no production timestamp field guarantee. Local file dates change on copy and newest conversation activity measures a different event. The first real-export validation must check which ZIP evidence is available and confirm the user-visible estimate label. [OpenAI export guide](https://help.openai.com/en/articles/7260999-exporting-your-chatgpt-history-and-data)
