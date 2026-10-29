# Data model

No new conversation schema or database migrations.

| Entity | Fields and validation | Lifecycle |
| --- | --- | --- |
| Environment | dev/e2e mode, internal/external proxy, alias, secret references, positive finite deadlines | validate before resource creation; secrets never serialized into reports |
| Run identity | unique lowercase Compose-safe token, project, bank, archive/state/engine volumes | allocated -> validated -> started -> initialized -> exercised -> cleaned; failure may enter cleanup at any stage |
| Initialization | bank, retain mission version/content, completion outcome | dependencies ready -> idempotent provisioning -> success/failure; failure blocks import |
| Report | run id, stage, pass/fail/skip, safe category, elapsed time, cleanup outcome | final only after cleanup attempt; preserve primary error |

Development project uses engineering-global and persistent volumes. E2E token determines unique project/bank and all disposable resources; no externally named shared volumes. Document ids and provenance remain owned by product models, not derived from run identity. Hard process termination can leave resources; report/recovery instructions use exact run identity rather than wildcard deletion.
