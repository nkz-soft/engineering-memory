# Workstation Data Model

- **Installed payload** is versioned and replaceable. It contains the CLI,
  runtime libraries, deployment assets and public setup examples.
- **Workstation profile** contains an app env file and a separate Compose env
  file. Both are private to the operator. The app file records absolute
  archive and SQLite paths and the local service endpoints. The Compose file
  records the selected provider and local service bindings. Existing values
  survive configuration retries and reinstall.
- **Durable state** consists of a stable Compose project volume for Hindsight
  and host directories for the archive and import-state database. Stack stop
  preserves the volume. Package replacement only replaces the installed payload.
- **Release candidate** binds a single tag and commit to two installed package
  versions and two SHA-256 sidecars. A candidate becomes public after both
  platform acceptance runs pass against those assets.
