# Operator contract — Recall evaluation

## Run recall

```text
engineering-memory evaluate recall --benchmark PATH --profile PATH --output PATH
```

`PATH` points to a benchmark manifest, a run profile JSON, or the destination report as appropriate. Load and validate inputs before starting the configured local stdio `engineering-memory serve` subprocess. Invoke `search_memory` with each question, the benchmark project tag, and the fixed limit. A valid tool response is a structured object with a `results` list whose members contain nonblank string document IDs and string content. Consume only those two fields. Route child stderr away from operator output so backend diagnostics cannot escape the fixed error categories.

On success, atomically write a complete JSON report and exit 0. On invalid input, failed or malformed recall, timeout, or write error, exit nonzero with a fixed error category and leave the destination untouched. No partial score or raw exception is printed.

## Compare reports

```text
engineering-memory evaluate compare --baseline PATH --candidate PATH --output PATH
```

Validate both reports and their comparison keys. On success, atomically write the JSON comparison and exit 0. On invalid or incompatible reports or write error, exit nonzero with a fixed error category and leave the destination untouched. Different run profiles are visible in the comparison so the operator can attribute differences using the recorded setup.
