# Data model: Re-import test evidence

No production schema change.

- Corpus member: source id, stable document id, original timestamp, original fact, optional replacement fact; exactly two members with distinct ids. Only one member changes in the edit case.
- Run observation: submitted document ids in order, imported/skipped/failed totals, before/after extraction calls/errors. Recorder forwards to the real store.
- Recall snapshot: all collected facts keyed by document id, expected identity set, expected fact per id. Reject empty/missing/unknown identities and duplicate fixture facts.
- Test lifecycle: fresh temporary archive/state and bank -> baseline import -> scenario-specific replay -> recall verification -> disposal and cleanup. Recovery transitions through closed/deleted SQLite state while preserving archive and bank. Edit uses intact state and a stable source id.

Facts are not documents. Distinct ids measure documents; deterministic one-fact fixture cardinality is an additional assertion, not a production data-model constraint.
