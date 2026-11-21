# Verification: Workstation outbound HTTP(S) proxy

**Date**: 2026-11-20

## Automated checks

| Command | Result |
| --- | --- |
| `python -m pytest --basetemp <worktree scratch> -q --tb=short -o faulthandler_timeout=45` using the locked release environment on Windows | 2,494 passed, 95 skipped |
| `ruff check .` | Passed |
| `ruff format --check .` | 750 files already formatted |
| `git diff --cached --check` | Passed |
| `gitleaks stdin --config /src/.gitleaks.toml --redact --no-banner` on the staged change, using the CI-pinned image | No leaks found |

The tests cover a legacy profile, setting and clearing a proxy, retaining values and cancelling changes, overlay selection, invalid bypass entries, and safe failure on timeout, upstream errors and invalid completion responses.

## Controlled routing

On Docker Engine 29.9.3 and Compose 5.7.0, the fixture origin lived on a private network accessible by the test proxy. LiteLLM had no direct route to the origin. The run used the bundled LiteLLM and Hindsight images. The HTTP proxy observed CONNECT for the HTTPS origin and an absolute-form forward request for the HTTP origin. A TLS-enabled replacement proxy also observed CONNECT using a fixture certificate trusted by the LiteLLM runtime. All three routes returned the expected synthetic completion, and the fixture origin recorded receipt.

The control with proxy settings absent and the repeat after clearing failed with HTTP 500. Incorrect proxy authentication also failed with HTTP 500 at LiteLLM, with the proxy recording the rejection. LiteLLM liveness and Hindsight readiness both returned HTTP 200 during these checks. Evidence records only status codes and fixture events.

## Release artifacts

- Windows 11 x64 built the PyInstaller payload and the Inno Setup executable. The final payload ran the guided wizard against an isolated profile and stack. A legacy profile passed configuration checks, both the initial and replacement authenticated proxies observed completions, and the wizard gave sanitized guidance on rejected authentication. After clearing the proxy and restarting the stack, the isolated origin was unreachable and both services stayed healthy. The test did not run the Inno installer against the host user profile.
- Ubuntu 24.04 WSL built the PyInstaller payload and Debian package using the repository's package script. The executable extracted from the DEB passed the same legacy-profile, set, replace, rejected-authentication and clear cycle using Docker Desktop through WSL. Both services were ready after clearing and the isolated origin was unreachable. This run did not invoke apt or the one-step Ubuntu installer from #105 / PR #106, which is pending on main.

## Review

A separate code review identified Docker client proxy inheritance into Hindsight, malformed bypass entries, and false-positive route checks on arbitrary HTTP 2xx responses. Each was reproduced in a test and fixed. The managed overlay now keeps Hindsight traffic direct, and the bounded check validates the completion response.
