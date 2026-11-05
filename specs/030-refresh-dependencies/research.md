# Research: Dependency upgrade

## Deployment images

Use the release tags and digests from issue #73. The tag communicates the release and the digest fixes the manifest used during verification. Confirm both platforms, upstream migration notes and actual startup and upgrade behavior during implementation. Rebuilding state from scratch alone would miss migration failures. [Hindsight release](https://github.com/vectorize-io/hindsight/releases/tag/v1.2.0) · [LiteLLM release](https://github.com/BerriAI/litellm/releases/tag/v1.108.0)

## Spec Kit migration

Use v1.3.0 in isolation and compare the generated output against the tracked integration. The current project records `feature_numbering: sequential`, `script: ps` and the Claude skills integration in `.specify/init-options.json`. A metadata-only edit would leave the generated skills and scripts at the old revision. [Spec Kit release](https://github.com/github/spec-kit/releases/tag/v1.3.0)

## CI and runtime

Review the requested major upgrades against their upstream runner and runtime requirements and verify on the hosted runner. Preserve the existing full-history checkout and finding-specific scanner exit code. Pin or otherwise align the resolved Python patch and uv version across CI and container builds where the published artifacts support it. Keep Gitleaks at the audited v8.30.1. [Checkout release](https://github.com/actions/checkout/releases/tag/v7.0.1) · [setup-uv release](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.3)
