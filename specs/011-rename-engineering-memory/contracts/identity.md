# Public Identity and Configuration Contract

| Surface | Required identity |
|---|---|
| Repository / distribution / CLI | `engineering-memory` |
| Import package | `engineering_memory` |
| Configuration prefix | `ENGINEERING_MEMORY_` |
| Nested delimiter | `__` (unchanged) |
| Container user | `engineering-memory`, UID 10001 |
| CI image tag | `engineering-memory:ci` |
| Shared memory bank | `engineering-global` (unchanged) |

The console command supports existing help and version behavior. Docker defaults to command help, prints usage and exits zero. Tracing service identifiers use the new project identity.

Only the new prefix configures this project, both in the process environment and optional environment files. Process environment retains precedence over file values. Consumer-prefixed variables, including invalid values, are ignored; former-prefix-only input still fails when required service settings are missing. Existing safe diagnostics and credential masking remain mandatory.

No compatibility package, command or environment alias is promised. Operators update environment keys and invocation names; local checkout directory and private data paths can remain unchanged. Genuine Hermes-consumer identifiers and explicit old-prefix regression inputs are not project identity leaks.
