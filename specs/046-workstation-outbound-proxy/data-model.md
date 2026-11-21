# Data Model: Workstation outbound HTTP(S) proxy

| Private Compose profile field | Value | Default |
| --- | --- | --- |
| `WORKSTATION_HTTP_PROXY` | Forward proxy URL for HTTP destinations | Absent |
| `WORKSTATION_HTTPS_PROXY` | Forward proxy URL for HTTPS destinations | Absent |
| `WORKSTATION_NO_PROXY` | Additional comma-separated bypass hosts | Absent |

A nonempty field selects the managed overlay. The effective bypass starts with `localhost,127.0.0.1,::1,hindsight,litellm` and adds validated operator entries. Cover IPv6 spelling and matching with the pinned transport. Reject a catch-all bypass that silently disables the configured route. Docker client defaults apply to the base stack when all fields are absent or empty.

Proxy URLs require an HTTP(S) scheme, a host, and a valid optional port. Permit percent-encoded userinfo and prohibit control characters, query strings, fragments and non-root paths. Preserve encoded credentials through the dotenv write/load and Compose interpolation round trip. URL input and stored values are treated as secrets. Keep retains the value, Set replaces it after validation, and Clear removes its effective value. Cancel keeps the previous profile. The next stack start applies the committed profile. There is no migration for old profiles.
