# Re-import verification contract

No public API or CLI change. Tests exercise the existing pipeline and MemoryStore contract.

| Scenario | Replay submissions | Extraction delta | Recall evidence |
|---|---|---|---|
| Unchanged, intact state | Empty | Exactly zero calls, zero errors | Both baseline ids and original facts, no additional documents |
| State deleted | Both original ids | May be nonzero; zero errors | Same exact document identity set and controlled fact cardinality |
| One conversation edited | Exactly changed id | Observe calls; zero errors | Same ids, changed fact updated, unchanged fact preserved, superseded fact absent |

Each scenario starts independently with a successful two-member baseline. Recall results must include both expected members and no unknown id; fact multiplicity is checked against the deterministic fixture. Query all members with generous supported limits. Empty or incomplete recall cannot pass.

Required runner checks must include all three new cases and every prior required case, reject missing or skipped results and reject failures/errors. Ordinary offline pytest explicitly skips live cases. Required Docker validation fails if prerequisites are unavailable. Keep existing lifecycle deadlines, serial execution and disposable bank cleanup.

Negative controls must reject a missing member, unexpected id, duplicated controlled fact, extra replay submission, nonzero unchanged extraction delta and submission of an incorrect edited identity. Controls use synthetic evidence and make no production writes.
