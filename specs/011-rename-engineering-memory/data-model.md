# Data Model

No domain entities, serialized fields, relationships or persistence transitions change.

The existing settings contract changes its input namespace only. Field validation, nested groups, secret types, defaults and precedence remain unchanged. Old-prefix-only input cannot satisfy required settings.

Conversation IDs, original timestamps, content hashes, provenance, tags, archive locations, import state and bank identity remain stable. No replay, re-extraction or data migration is required.
