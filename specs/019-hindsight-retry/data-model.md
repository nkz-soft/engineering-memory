# Retry data model

No public domain model, database or archive schema changes.

## Retry policy

Private immutable configuration: maximum total attempts (positive integer, default 4), initial delay (positive finite seconds, default 1), maximum delay (finite and at least initial, default 8), jitter (finite nonnegative seconds, default 1). Clock and sleep seams support deterministic tests. No environment/CLI or persisted settings added.

## Logical operation

Existing operation kind, absolute monotonic deadline, bank and optional document ID. Retain associates a content fingerprint and UUID with a document in _pending; serialization happens before attempts. Recall has no retain UUID and never logs its query.

Transitions: validated → submitting → acknowledged → polling → completed. A transient request failure waits and retries that same request; permanent errors terminate. Exhaustion preserves uncertain retain identity; completion/definitive extraction failure keeps existing cleanup. A rejected replay preserves prior uncertainty.

## Request attempt

Request kind, request ordinal, one-based attempt number, elapsed time, optional allowlisted status/category and next delay. Attempts correlate via operation UUID where available. Attempt number resets for a new polling request. No body, query, header or upstream exception objects enter logs.
