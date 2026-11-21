# Data model

| Field | New-profile source | Update rule |
| --- | --- | --- |
| Provider and model | OpenRouter preselected with the editable model `openai/gpt-oss-20b` | Split on the first slash of the stored LiteLLM model ID. Preserve unknown provider prefixes and the rest of the ID verbatim. Prepend the selected provider prefix once when composing the ID. |
| Provider API base | OpenRouter preset or provider-specific/empty input | Empty means use the provider default. Keep blank saved values blank. |
| Provider key | Empty | Read only an indicator of a usable saved key. Blank keeps the existing assignment for the same provider. A replacement is required for a new provider. |
| Memory backend and LiteLLM ports | 8888 and 4000 | Distinct integers in 1–65535. Continue binding the host ports to loopback. |
| Archive and SQLite | Existing workstation data defaults | Validate absolute paths and existing types with the current workstation checks. Store the choice without relocating data. |
| Outbound proxies, bypass and local LiteLLM key | Existing private profile rules | Preserve existing assignments and local key. Generate a local key when first required. |

The saved files are the existing `compose.env` and `app.env` under the per-user configuration directory. The wizard also carries transient edited values and a startup consent flag. Consent is withdrawn when the operator defers or cancels, and is never persisted.
