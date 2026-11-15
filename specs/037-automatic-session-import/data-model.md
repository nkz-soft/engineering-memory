# Data Model: Automatic Coding-Agent Session Import

## Configured source

A source kind (`codex` or `claude-code`) and an operator-approved root. At least one root is required. Validate the quiet period as a positive duration. A root unavailable at run time produces an outcome for that source while remaining sources proceed.

## Snapshot candidate

A regular main-session JSONL file in a supported layout. The source identity, length and modification metadata observed for capture are transient and are checked again before the copy is accepted. An accepted snapshot owns the original bytes until the existing adapter and pipeline consume it. Its path is private and temporary.

An eligible candidate proceeds through discovery → capture → parse → existing import. Recent, changing or disappearing candidates are deferred. Stable malformed, unreadable or unsupported candidates are reported. Every run discovers candidates again, including previously deferred ones. The existing normalized content hash determines whether extraction is needed.

## Source outcome

For each configured source, report imported, unchanged, deferred and failed counts plus a category for a source-level failure. Count candidates ending in capture or parse errors as failed and keep source-level errors visible even when no file could be opened. Session IDs, local paths and raw error messages are unnecessary in this summary.

## Run ownership

A temporary OS lock is scoped to the effective import-state path. It guards the full capture run and is released on exit. The raw archive and import-state schema remain the authoritative persistent records.
