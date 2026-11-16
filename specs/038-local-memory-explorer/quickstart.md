# Validation: Local Memory Explorer

Use an isolated, configured workstation profile and a previously imported synthetic corpus. Seed a shared search term in two projects, a two-session question in the target project and a citation after message 50. Include an HTML-looking tool result.

1. Launch `engineering-memory explore`, open its loopback address and enter the displayed credential. In a second browser context, verify that unauthenticated data calls fail.
2. Search the target project. Open a match, check its source and original timestamp, and read a later transcript page. Confirm the competing project is absent and the HTML-looking text remains inert.
3. Ask the cross-session question. Compare the answer, citations and transcript with the same CLI and MCP calls in a controlled run with deterministic synthesis. Select the late citation and verify the exact message, field and quote.
4. Exercise an empty search, a partial answer, insufficient evidence, failed verification, an unavailable backend and synthesis missing. Verify distinct states and retry with the submitted input intact. Verify search still works when only synthesis is missing.
5. Verify browser access stops after the launcher exits. Repeat the launch and core journeys from the wheel on Windows 11 and Ubuntu 24.04.

Run `uv run --locked pytest -q`, `uv run --locked ruff check .` and `uv run --locked ruff format --check .`. Record observed output and platform or backend checks in the implementation PR.
