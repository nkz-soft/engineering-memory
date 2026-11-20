"""Run the local explorer in Chromium when ENGINEERING_MEMORY_BROWSER is set."""

import os
import socket
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

import pytest
import uvicorn

from engineering_memory.access.service import AccessError, MemoryAccess, SynthesisUnconfigured

TOKEN = "browser-fixture-key"
MARKUP = '<img src=x onerror="alert(1)">'
PROVENANCE = {"source": "codex", "project": "orchard"}


@pytest.fixture
def explorer(request):
    browser_channel = os.environ.get("ENGINEERING_MEMORY_BROWSER")
    if not browser_channel:
        pytest.skip("set ENGINEERING_MEMORY_BROWSER to chromium or msedge")
    from playwright.sync_api import sync_playwright

    from engineering_memory.api.explorer import create_explorer_app

    build_access = getattr(request, "param", None)
    access = build_access() if build_access else Mock(spec=MemoryAccess)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        authority = f"127.0.0.1:{listener.getsockname()[1]}"
        app = create_explorer_app(
            access,
            token=TOKEN,
            authority=authority,
            read_status=getattr(access, "read_status", None),
        )
        server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level="warning"))
        with ThreadPoolExecutor() as pool, sync_playwright() as playwright:
            running = pool.submit(server.run, sockets=[listener])
            try:
                browser = playwright.chromium.launch(
                    channel=None if browser_channel == "chromium" else browser_channel
                )
                try:
                    page = browser.new_page()
                    page.set_default_timeout(5000)
                    navigation = page.goto(f"http://{authority}/", timeout=10000)
                    assert navigation is not None and navigation.ok
                    page.get_by_label("Access key").fill(TOKEN)
                    page.get_by_role("button", name="Unlock").click()
                    yield page, access
                finally:
                    browser.close()
            finally:
                server.should_exit = True
                running.result(timeout=10)


def _page(offset, text, *, tools=(), next_offset=None):
    return {
        "document_id": "codex:one",
        "started_at": "2026-01-01T00:00:00Z",
        "provenance": PROVENANCE,
        "offset": offset,
        "next_offset": next_offset,
        "messages": [
            {
                "role": "assistant",
                "text": text,
                "sent_at": "2026-01-01T00:00:03Z",
                "tool_activity": list(tools),
            }
        ],
    }


def _query(page, mode, query="queue"):
    page.get_by_label("Project slug").fill("orchard")
    page.get_by_label("Question or search terms").fill(query)
    page.get_by_role("button", name=mode, exact=True).click()


def test_search_and_pagination_use_public_provenance(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    access.search_memory.return_value = {
        "results": [
            {
                "document_id": "codex:one",
                "content": MARKUP,
                "started_at": "2026-01-01T00:00:00Z",
                "provenance": PROVENANCE,
            }
        ]
    }
    access.get_conversation.side_effect = [
        _page(0, "First page", next_offset=50),
        _page(50, "Later page"),
    ]

    _query(page, "Search")

    expect(page.get_by_text(MARKUP, exact=True)).to_be_visible()
    assert page.locator("img").count() == 0
    page.get_by_role("button", name="Open conversation").click()
    expect(page.get_by_text("First page")).to_be_visible()
    expect(page.get_by_text("2026-01-01T00:00:03Z", exact=False)).to_be_visible()
    page.get_by_role("button", name="Next messages").click()
    expect(page.get_by_text("Later page")).to_be_visible()
    expect(page.get_by_role("button", name="Next messages")).to_be_hidden()
    access.search_memory.assert_called_once_with(query="queue", tags=["project:orchard"])


def test_deep_recall_opens_exact_tool_evidence_and_rejects_stale_quote(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    access.deep_recall.return_value = {
        "status": "partial",
        "uncertainty": ["synthesis_uncertain"],
        "coverage": {"archive_loads": 2},
        "timeline": [
            {
                "text": "Retries changed.",
                "citations": [
                    {
                        "document_id": "codex:one",
                        "message_index": 52,
                        "timestamp": "2026-01-01T00:00:03+00:00",
                        "field": "tool_result",
                        "tool_index": 0,
                        "quote": "Retry succeeded.",
                    }
                ],
            }
        ],
    }
    moved = _page(52, None, tools=[{"result": "Retry succeeded."}])
    moved["messages"][0]["sent_at"] = "2026-01-01T00:01:03Z"
    access.get_conversation.side_effect = [
        _page(52, None, tools=[{"result": "Retry   succeeded."}]),
        _page(52, None, tools=[{"result": "Different evidence."}]),
        moved,
    ]

    _query(page, "Deep Recall")
    expect(page.get_by_text("Partial answer")).to_be_visible()
    link = page.get_by_role("button", name="Open cited message")
    link.click()
    expect(page.locator("mark")).to_have_text("Retry succeeded.")
    access.get_conversation.assert_called_once_with(
        document_id="codex:one", offset=52, page_size=50
    )

    link.click()
    expect(page.get_by_text("Cited evidence is unavailable.")).to_be_visible()
    expect(page.locator("mark")).to_have_count(0)

    link.click()
    expect(page.get_by_text("Cited evidence is unavailable.")).to_be_visible()
    expect(page.locator("mark")).to_have_count(0)


@pytest.mark.parametrize(
    ("error", "label"),
    [
        (AccessError("unavailable"), "This operation is unavailable."),
        (SynthesisUnconfigured(), "Deep Recall needs synthesis configuration."),
    ],
)
def test_empty_and_unavailable_preserve_input(explorer, error, label):
    from playwright.sync_api import expect

    page, access = explorer
    access.search_memory.return_value = {"results": []}
    access.deep_recall.side_effect = error

    _query(page, "Search")
    expect(page.get_by_text("No matches in this project.")).to_be_visible()
    page.get_by_role("button", name="Deep Recall", exact=True).click()
    expect(page.get_by_text(label)).to_be_visible()
    expect(page.get_by_label("Question or search terms")).to_have_value("queue")
    expect(page.get_by_label("Project slug")).to_have_value("orchard")


@pytest.mark.parametrize(
    ("state", "label"),
    [
        ("insufficient_evidence", "There is insufficient evidence for an answer."),
        ("verification_failed", "The answer could not be verified."),
    ],
)
def test_distinguishes_unsuccessful_answer_states(explorer, state, label):
    from playwright.sync_api import expect

    page, access = explorer
    access.deep_recall.return_value = {
        "status": state,
        "coverage": {},
        "uncertainty": [],
        "timeline": [],
    }
    _query(page, "Deep Recall")
    expect(page.get_by_text(label)).to_be_visible()


def test_new_scope_replaces_in_flight_search(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    started = Event()
    finish = Event()

    def search(*, query, tags):
        if tags == ["project:orchard"]:
            started.set()
            assert finish.wait(10)
            return {
                "results": [
                    {
                        "document_id": "codex:old",
                        "content": "Old response",
                        "provenance": PROVENANCE,
                    }
                ]
            }
        return {"results": []}

    access.search_memory.side_effect = search
    try:
        _query(page, "Search")
        assert started.wait(5)
        page.get_by_label("Project slug").fill("cypress")
        page.get_by_role("button", name="Search", exact=True).click()
        expect(page.get_by_text("No matches in this project.")).to_be_visible()
        assert access.search_memory.call_args.kwargs["tags"] == ["project:cypress"]
        assert page.get_by_text("Old response").count() == 0
    finally:
        finish.set()


def test_fresh_browser_context_cannot_read_memory(explorer):
    page, access = explorer
    assert page.context.browser is not None
    second = page.context.browser.new_page()
    try:
        second.goto(page.url)
        status = second.evaluate(
            """async () => {
                const response = await fetch("/api/search", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({query: "queue", project: "orchard"}),
                });
                return response.status;
            }"""
        )
        assert status == 401
        assert not access.mock_calls
    finally:
        second.close()


def test_decision_history_shows_uncertainty_and_opens_exact_evidence(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    timestamp = "2026-01-01T00:00:03Z"
    action = {
        "document_id": "codex:one",
        "message_index": 51,
        "field": "text",
        "timestamp": timestamp,
        "quote": "Use hourly caching.",
    }
    base = {
        "kind": "proposal",
        "version": "Daily caching",
        "prior_version": None,
        "reason": None,
        "action": action,
        "context": [],
        "occurred_at": timestamp,
        "chronology": "known",
        "ordering_uncertain": True,
    }
    access.decision_history.return_value = {
        "project": "orchard",
        "topic": "queue",
        "status": "partial",
        "coverage": {},
        "uncertainty": ["unresolved_conflict", "unknown_time"],
        "events": [
            base,
            base | {"kind": "adoption"},
            base
            | {
                "kind": "revision",
                "occurred_at": None,
                "chronology": "unknown",
                "ordering_uncertain": False,
            },
            base
            | {
                "kind": "supersession",
                "version": "Hourly caching",
                "prior_version": "Daily caching",
                "reason": "Reduce staleness",
            },
        ],
        "conflicts": [
            {
                "summary": "Rollout disputed",
                "accounts": [
                    {"text": "Daily remains active", "citations": [action]},
                    {"text": "Hourly is active", "citations": [action]},
                ],
            }
        ],
    }
    access.get_conversation.side_effect = [
        _page(51, "Use hourly caching."),
        _page(51, "Source changed."),
    ]

    _query(page, "Decision history")
    for heading in ("Proposal", "Adoption", "Revision", "Supersession", "Unresolved conflicts"):
        expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
    for text in (
        "Reduce staleness",
        "Date unknown",
        "Order uncertain",
        "Daily remains active",
        "Hourly is active",
    ):
        expect(page.get_by_text(text, exact=True).first).to_be_visible()
    source = page.get_by_role("button", name="Open event source").first
    source.click()
    expect(page.locator("mark")).to_have_text("Use hourly caching.")
    access.get_conversation.assert_called_with(document_id="codex:one", offset=51, page_size=50)
    source.click()
    expect(page.get_by_text("Cited evidence is unavailable.")).to_be_visible()
    page.get_by_label("Project slug").fill("another")
    expect(page.get_by_role("heading", name="Unresolved conflicts")).to_have_count(0)


def _decision_access():
    from types import SimpleNamespace

    from engineering_memory.normalization import Source
    from tests.unit.test_deep_recall import record

    old = record(Source.CODEX, "old", "Adopt daily caching.", project="orchard")
    new = record(
        Source.CLAUDE_CODE,
        "new",
        "Replace daily caching with hourly to reduce staleness.",
        days=1,
        project="orchard",
    )
    foreign = record(Source.CODEX, "foreign", "Private competing project.", project="other")
    memory, archive, synthesis = Mock(), Mock(), Mock()
    memory.recall.return_value = [
        SimpleNamespace(provenance=row.provenance) for row in (new, foreign, old)
    ]
    archive.load.side_effect = {row.document_id: row for row in (old, new)}.__getitem__

    def decision(_query, passages, _times):
        by_text = {text: selector for selector, text in passages.items()}
        assert set(by_text) == {
            old.conversation.messages[0].text,
            new.conversation.messages[0].text,
        }
        previous = {"selector": by_text[old.conversation.messages[0].text]}
        current = {"selector": by_text[new.conversation.messages[0].text]}
        return {
            "events": [
                {"kind": "adoption", "version": "Daily caching", "action": previous},
                {
                    "kind": "supersession",
                    "version": "Hourly caching",
                    "prior_version": "Daily caching",
                    "reason": "Reduce staleness",
                    "action": current,
                    "context": [previous],
                },
            ]
        }

    synthesis.synthesize_decisions.side_effect = decision
    return MemoryAccess(memory, archive, synthesis=synthesis)


@pytest.mark.parametrize("explorer", [_decision_access], indirect=True)
def test_real_decision_read_opens_sources_from_both_sessions(explorer):
    from playwright.sync_api import expect

    page, _ = explorer
    _query(page, "Decision history")
    expect(page.locator(".decision-events h4")).to_have_text(["Adoption", "Supersession"])
    expect(page.get_by_text("Previous version · Daily caching", exact=True)).to_be_visible()
    expect(page.get_by_text("Reduce staleness", exact=True)).to_be_visible()
    expect(page.get_by_text("Private competing project.")).to_have_count(0)
    sources = page.get_by_role("button", name="Open event source")
    sources.nth(0).click()
    expect(page.locator("mark")).to_have_text("Adopt daily caching.")
    sources.nth(1).click()
    expect(page.locator("mark")).to_have_text(
        "Replace daily caching with hourly to reduce staleness."
    )


@pytest.mark.parametrize(
    "status,label",
    [
        ("insufficient_evidence", "There is insufficient evidence for this decision."),
        ("verification_failed", "The decision history could not be verified."),
    ],
)
def test_decision_history_distinguishes_empty_and_failed(explorer, status, label):
    from playwright.sync_api import expect

    page, access = explorer
    access.decision_history.return_value = {
        "status": status,
        "events": [],
        "conflicts": [],
        "uncertainty": [status],
    }
    _query(page, "Decision history")
    expect(page.get_by_text(label, exact=True)).to_be_visible()


def test_lock_aborts_pending_decision_history(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    started, release, finished = Event(), Event(), Event()

    def history(**_arguments):
        started.set()
        release.wait(10)
        finished.set()
        return {"status": "completed", "events": [], "conflicts": [], "uncertainty": []}

    access.decision_history.side_effect = history
    page.wait_for_function("""() => {
      const fetchRequest = window.fetch;
      window.fetch = (...args) => {
        const signal = args[1]?.signal;
        signal?.addEventListener("abort", () => { window.decisionReadAborted = true; });
        return fetchRequest.apply(window, args);
      };
      return true;
    }""")
    _query(page, "Decision history")
    try:
        assert started.wait(5)
        page.get_by_role("button", name="Lock", exact=True).click()
        page.wait_for_function("() => window.decisionReadAborted === true")
    finally:
        release.set()
    assert finished.wait(5)
    page.get_by_label("Access key").fill(TOKEN)
    page.get_by_role("button", name="Unlock").click()
    expect(page.get_by_text("Decision history ready.")).to_have_count(0)


@pytest.mark.parametrize(
    ("name", "recorded_request", "result", "expected"),
    [
        (
            "Bash",
            '{"id":"a","input":{"command":"echo safe"}}',
            '{"tool_use_id":"a","is_error":true,"content":"failed"}',
            "Recorded error",
        ),
        (
            "exec_command",
            '{"call_id":"a","arguments":"{"cmd":"echo safe"}"}',
            '{"call_id":"a","output":"done"}',
            "done",
        ),
        (
            "Edit",
            '{"id":"b","input":{"old_string":"old line","new_string":"new line"}}',
            None,
            "Recorded edit: before / after",
        ),
        (
            "apply_patch",
            '{"call_id":"p","input":"*** Begin Patch\\n-old\\n+new\\n*** End Patch"}',
            "",
            "Recorded patch",
        ),
    ],
)
def test_session_recorded_fields(explorer, name, recorded_request, result, expected):
    from playwright.sync_api import expect

    page, access = explorer
    access.search_memory.return_value = {
        "results": [
            {
                "document_id": "codex:one",
                "content": "session",
                "provenance": PROVENANCE,
            }
        ]
    }
    access.get_conversation.return_value = _page(
        0, "Dialogue", tools=[{"name": name, "request": recorded_request, "result": result}]
    )
    _query(page, "Search")
    page.get_by_role("button", name="Open conversation").click()
    expect(page.get_by_text(expected, exact=True)).to_be_visible()
    expect(page.get_by_text("No result recorded on this occurrence.", exact=True)).to_have_count(
        1 if result is None else 0
    )
    expect(page.get_by_text("Empty result.", exact=True)).to_have_count(1 if result == "" else 0)


@pytest.mark.parametrize("offset", [0, 49, 50, 100])
def test_session_fragment_exact_tool_and_reload(explorer, offset):
    from playwright.sync_api import expect

    page, access = explorer
    access.get_conversation.return_value = _page(
        offset,
        "target",
        tools=[
            {
                "name": "exec",
                "request": "recorded command",
                "result": "evidence\n" * 10000,
            }
        ],
    )
    fragment = (
        "#view=session&project=orchard&document=codex%3Aone"
        f"&message={offset}&tool=0&field=tool_result"
    )
    page.goto(page.url.split("#")[0] + fragment)
    page.reload()
    page.get_by_label("Access key").fill(TOKEN)
    page.get_by_role("button", name="Unlock").click()
    target = page.locator('[data-field="tool_result"].cited')
    expect(target).to_be_visible()
    expect(target.locator(".full-output pre").first).to_have_text("evidence\n" * 10000)
    expect(target).to_be_focused()
    access.get_conversation.assert_called_with(document_id="codex:one", offset=offset, page_size=50)
    link = target.get_by_role("link", name="Link to result")
    assert TOKEN not in link.get_attribute("href")
    assert "evidence" not in link.get_attribute("href")
    target.locator("summary").first.click()
    link.click()
    expect(target).to_be_focused()
    expect(target.locator("details.full-output").first).to_have_attribute("open", "")


@pytest.mark.parametrize(
    "suffix",
    [
        "&message=-1",
        "&message=1.2",
        "&message=0&message=1",
        "&message=0&tool=0&field=text",
        "&message=0&field=tool_result",
        "&message=0&unknown=yes",
        "&message=9007199254740992",
    ],
)
def test_session_rejects_bad_fragment(explorer, suffix):
    from playwright.sync_api import expect

    page, access = explorer
    page.evaluate(
        "location.hash = " + repr("#view=session&project=orchard&document=codex%3Aone" + suffix)
    )
    expect(page.get_by_text("Session target is unavailable.", exact=True)).to_be_visible()
    access.get_conversation.assert_not_called()


def test_session_collapses_and_expands_complete_output(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    output = "synthetic output\n" * 10000 + MARKUP
    access.search_memory.return_value = {
        "results": [
            {
                "document_id": "codex:one",
                "content": "session",
                "provenance": PROVENANCE,
            }
        ]
    }
    access.get_conversation.return_value = _page(
        0, "Dialogue", tools=[{"name": "exec", "request": None, "result": output}]
    )
    _query(page, "Search")
    page.get_by_role("button", name="Open conversation").click()
    field = page.locator('[data-field="tool_result"]')
    disclosure = field.locator("details").first
    expect(disclosure).not_to_have_attribute("open", "")
    expect(field.locator(".preview")).to_be_visible()
    summary = disclosure.locator("summary").first
    summary.focus()
    page.keyboard.press("Enter")
    expect(disclosure).to_have_attribute("open", "")
    expect(disclosure.locator("pre").first).to_have_text(output)
    assert page.locator("img").count() == 0


def test_session_long_envelope_and_nontext(explorer):
    import json

    from playwright.sync_api import expect

    page, access = explorer
    output = "decoded log\n" * 1000
    access.search_memory.return_value = {
        "results": [
            {
                "document_id": "codex:one",
                "content": "session",
                "provenance": PROVENANCE,
            }
        ]
    }
    record = _page(
        0,
        "prose\n" * 1000,
        tools=[
            {
                "name": "exec",
                "result": json.dumps({"call_id": "a", "output": output}),
            }
        ],
    )
    record["messages"][0]["non_text_parts"] = [{"kind": "image"}]
    access.get_conversation.return_value = record
    _query(page, "Search")
    page.get_by_role("button", name="Open conversation").click()
    expect(page.get_by_text("Archived non-text content: image", exact=True)).to_be_visible()
    field = page.locator('[data-field="tool_result"]')
    field.get_by_text("Show complete recorded output", exact=True).click()
    expect(field.get_by_text(output, exact=True)).to_be_visible()
    expect(page.locator(".message > .long-text details")).not_to_have_attribute("open", "")


def _session_access():
    from engineering_memory.normalization import Source, ToolActivity
    from tests.unit.test_deep_recall import record

    rows = {}
    for source in (Source.CODEX, Source.CLAUDE_CODE):
        row = record(source, "session", "sanitized dialogue", project="orchard")
        message = row.conversation.messages[0].model_copy(
            update={
                "tool_activity": (ToolActivity(name="unknown-tool", result="literal output"),),
            }
        )
        row = row.model_copy(
            update={
                "conversation": row.conversation.model_copy(
                    update={
                        "messages": (message,) * 101,
                    }
                )
            }
        )
        rows[row.document_id] = row
    archive = Mock()
    archive.load.side_effect = rows.__getitem__
    return MemoryAccess(Mock(), archive)


@pytest.mark.parametrize("explorer", [_session_access], indirect=True)
@pytest.mark.parametrize("source", ["codex", "claude-code"])
def test_session_real_read_message_history_and_missing_tool(explorer, source):
    from playwright.sync_api import expect

    page, access = explorer
    base = f"#view=session&project=orchard&document={source}%3Asession&message="
    page.evaluate("location.hash = " + repr(base + "50"))
    expect(page.locator(".message.cited")).to_be_focused()
    expect(page.locator(".message.cited")).to_have_attribute("data-message", "50")
    page.evaluate("location.hash = " + repr(base + "100"))
    expect(page.locator(".message.cited")).to_have_attribute("data-message", "100")
    page.go_back()
    expect(page.locator(".message.cited")).to_have_attribute("data-message", "50")
    page.evaluate("location.hash = " + repr(base + "100&tool=9&field=tool_result"))
    expect(page.get_by_text("Session target is unavailable.", exact=True)).to_be_visible()
    expect(page.locator(".message")).to_have_count(0)
    access.archive.load_original.assert_not_called()


class StatusAccess:
    def get_conversation(self, **_):
        raise AccessError("not_found")

    def read_status(self, project):
        from datetime import UTC, datetime

        from engineering_memory.access.status import ExplorerStatus
        from engineering_memory.ingestion.health import ProjectImportEvidence, SourceHealth

        imported = datetime(2026, 11, 19, tzinfo=UTC)
        refreshed = datetime(2026, 11, 18, tzinfo=UTC)
        return ExplorerStatus(
            lambda scope: (
                [
                    SourceHealth(
                        source="codex",
                        outcome="failed",
                        last_attempt_at=imported,
                        last_success_at=refreshed,
                        error_categories=("source",),
                    )
                ],
                ProjectImportEvidence(started_at=imported, completed_at=imported)
                if scope == "orchard"
                else None,
            ),
            self,
        ).read(project)

    def get_project_model_metadata(self, key):
        from datetime import UTC, datetime

        from engineering_memory.memory.interface.project_models import ProjectModelMetadata

        return ProjectModelMetadata(
            refresh_state="ready",
            last_refreshed_at=datetime(2026, 11, 18, tzinfo=UTC),
        )


@pytest.mark.parametrize("explorer", [StatusAccess], indirect=True)
def test_status_handles_project_change_and_lock(explorer):
    from playwright.sync_api import expect

    page, _ = explorer
    page.get_by_label("Project slug").fill("orchard")
    page.get_by_role("button", name="Status", exact=True).click()
    status = page.get_by_role("region", name="Import and model status")
    expect(status.get_by_text("Codex", exact=True)).to_be_visible()
    expect(status.get_by_text("Last successful import", exact=False).last).to_be_visible()
    expect(status.get_by_text("Stale", exact=True)).to_have_count(3)
    page.get_by_label("Project slug").fill("another")
    expect(status.get_by_text("Unknown", exact=True)).to_have_count(3)
    expect(status.get_by_text("Stale", exact=True)).to_have_count(0)
    page.evaluate(
        "location.hash = '#view=session&project=orchard&document=codex%3Afixture&message=0'"
    )
    expect(status.get_by_text("Stale", exact=True)).to_have_count(3)
    page.get_by_role("button", name="Lock", exact=True).click()
    expect(status).to_be_hidden()
    expect(page.locator("#status-rows")).to_be_empty()


def test_session_handoff_copy_and_denial(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    target = "#view=session&project=orchard&document=codex%3Aone&message=0"
    access.get_conversation.return_value = _page(0, "Selected session")
    markdown = "# Session handoff\n\n## Goal\n\n" + MARKUP
    access.session_handoff.return_value = {"markdown": markdown}
    page.goto(page.url + target)
    page.evaluate(
        """() => {
            window.copiedMarkdown = null;
            window.denyClipboard = false;
            navigator.clipboard.writeText = async (text) => {
                if (window.denyClipboard) throw new Error("denied");
                window.copiedMarkdown = text;
            };
        }"""
    )

    page.get_by_role("button", name="Generate handoff").click()
    brief = page.get_by_role("textbox", name="Handoff Markdown")
    expect(brief).to_have_value(markdown)
    assert page.locator("img").count() == 0
    page.get_by_role("button", name="Copy Markdown").click()
    expect(page.get_by_text("Markdown copied.")).to_be_visible()
    assert page.evaluate("window.copiedMarkdown") == markdown

    page.evaluate("window.denyClipboard = true")
    page.get_by_role("button", name="Copy Markdown").click()
    expect(page.get_by_text("Clipboard unavailable. Copy the Markdown manually.")).to_be_visible()
    expect(brief).to_have_value(markdown)
    access.session_handoff.assert_called_once()
    assert [call[0] for call in access.mock_calls] == ["get_conversation", "session_handoff"]

    page.get_by_role("button", name="Lock").click()
    expect(brief).to_have_count(0)


def test_session_handoff_discards_late_result_after_reopening_same_session(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    target = "#view=session&project=orchard&document=codex%3Aone&message=0"
    access.get_conversation.return_value = _page(0, "Selected session")
    started, release, finished = Event(), Event(), Event()

    def delayed(**kwargs):
        started.set()
        try:
            assert release.wait(10)
            return {"markdown": "Old handoff content"}
        finally:
            finished.set()

    access.session_handoff.side_effect = delayed
    page.goto(page.url + target)
    generate = page.get_by_role("button", name="Generate handoff")
    page.get_by_role("button", name="Generate handoff").click()
    try:
        assert started.wait(5)
        page.get_by_role("button", name="Lock").click()
        page.get_by_label("Access key").fill(TOKEN)
        page.get_by_role("button", name="Unlock").click()
        expect(generate).to_be_enabled()
    finally:
        release.set()
    assert finished.wait(5)
    expect(page.get_by_role("textbox", name="Handoff Markdown")).to_have_count(0)

    access.session_handoff.side_effect = None
    access.session_handoff.return_value = {"markdown": "Fresh handoff content"}
    generate.click()
    expect(page.get_by_role("textbox", name="Handoff Markdown")).to_have_value(
        "Fresh handoff content"
    )


def test_neighborhood_reroots_and_opens_guarded_evidence(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    access.get_conversation.return_value = _page(0, "Selected session")
    session = {"kind": "session", "identity": "codex:one", "label": "Selected session"}
    file = {
        "kind": "file",
        "identity": "src/app.py",
        "label": "src/app.py",
        "repository": "example/orchard",
    }
    roots = []
    guarded = []
    snapshot = "a" * 64

    def neighborhood(route):
        body = route.request.post_data_json
        assert body["project"] == "orchard"
        roots.append(body["root"])
        route.fulfill(
            json={
                "status": "partial",
                "edges": [
                    {"origin": session, "target": file, "relation": "file_edit", "handle": "edit"}
                ],
                "truncated": True,
            }
        )

    def conversation(route):
        body = route.request.post_data_json
        if "snapshot" not in body:
            route.continue_()
            return
        guarded.append(body)
        if len(guarded) == 1:
            route.fulfill(json=_page(51, "Edit", tools=[{"result": MARKUP}]))
        else:
            route.fulfill(status=404, json={"error": "not_found"})

    page.route("**/api/neighborhood", neighborhood)
    page.route("**/api/conversation", conversation)
    page.route(
        "**/api/neighborhood/evidence",
        lambda route: route.fulfill(
            json={
                "relation": "file_edit",
                "text": MARKUP,
                "selector": {
                    "document_id": "codex:one",
                    "message": 51,
                    "tool": 0,
                    "field": "tool_result",
                    "snapshot": snapshot,
                },
            }
        ),
    )

    page.goto(page.url + "#view=session&project=orchard&document=codex%3Aone&message=0")
    page.get_by_role("button", name="Open session neighborhood").click(timeout=1500)
    panel = page.get_by_role("region", name="Evidence neighborhood")
    expect(panel.get_by_text("Index coverage is partial.", exact=False)).to_be_visible()
    expect(panel.get_by_text("Showing a limited set", exact=False)).to_be_visible()
    page.get_by_role("button", name="Browse src/app.py").press("Enter")
    expect(panel.get_by_role("button", name="Browse Selected session")).to_be_visible()
    assert roots == [
        {"kind": "session", "identity": "codex:one"},
        {"kind": "file", "identity": "src/app.py", "repository": "example/orchard"},
    ]
    page.get_by_role("button", name="Inspect recorded file edit").press("Enter")
    expect(panel.get_by_text(MARKUP, exact=True)).to_be_visible()
    assert page.locator("img").count() == 0
    link = panel.get_by_role("link", name="Open supporting field")
    assert "snapshot=" + snapshot in link.get_attribute("href")
    assert "onerror" not in link.get_attribute("href")
    link.click()
    field = page.locator('[data-field="tool_result"].cited')
    expect(field).to_be_focused()
    assert guarded == [
        {
            "document_id": "codex:one",
            "offset": 51,
            "page_size": 50,
            "project": "orchard",
            "snapshot": snapshot,
        }
    ]
    expect(panel).to_be_hidden()
    field.get_by_role("link", name="Link to result").click()
    expect(page.get_by_text("Cited evidence is unavailable.")).to_be_visible()
    expect(page.get_by_text(MARKUP, exact=True)).to_have_count(0)
    assert guarded == guarded[:1] * 2


def test_exact_file_neighborhood_distinguishes_index_states_and_clears_on_lock(explorer):
    from playwright.sync_api import expect

    page, _ = explorer
    calls = []

    def neighborhood(route):
        calls.append(route.request.post_data_json)
        route.fulfill(
            json={
                "status": "unindexed" if len(calls) == 1 else "ready",
                "edges": [],
                "truncated": False,
            }
        )

    page.route("**/api/neighborhood", neighborhood)
    page.get_by_label("Project slug").fill("orchard")
    page.get_by_role("button", name="Browse a file").click(timeout=1500)
    page.get_by_label("Repository identity").fill("example/orchard")
    page.get_by_label("Project-relative file path").fill("src/app.py")
    page.get_by_role("button", name="Open file neighborhood").click()
    panel = page.get_by_role("region", name="Evidence neighborhood")
    expect(panel.get_by_text("This project has no neighborhood index.")).to_be_visible()
    page.get_by_role("button", name="Open file neighborhood").click()
    expect(panel.get_by_text("No recorded links for this root.")).to_be_visible()
    assert (
        calls
        == [
            {
                "project": "orchard",
                "root": {"kind": "file", "identity": "src/app.py", "repository": "example/orchard"},
            }
        ]
        * 2
    )
    page.get_by_role("button", name="Lock", exact=True).click()
    expect(panel).to_be_hidden()
    expect(page.get_by_label("Project-relative file path")).to_have_value("")


def test_neighborhood_discards_evidence_response_after_reroot(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    access.get_conversation.return_value = _page(0, "Selected session")
    session = {"kind": "session", "identity": "codex:one", "label": "Selected session"}
    file = {"kind": "file", "identity": "notes.md", "repository": "example/orchard"}
    requests = []

    def neighborhood(route):
        is_file = route.request.post_data_json["root"]["kind"] == "file"
        route.fulfill(
            json={
                "status": "ready",
                "edges": []
                if is_file
                else [
                    {"origin": session, "target": file, "relation": "file_edit", "handle": "first"},
                ],
                "truncated": False,
            }
        )

    page.route("**/api/neighborhood", neighborhood)
    page.route("**/api/neighborhood/evidence", lambda route: requests.append(route))
    page.goto(page.url + "#view=session&project=orchard&document=codex%3Aone&message=0")
    page.get_by_role("button", name="Open session neighborhood").click()
    with page.expect_request("**/api/neighborhood/evidence"):
        page.get_by_role("button", name="Inspect recorded file edit").click()
    page.get_by_role("button", name="Browse notes.md").click()
    expect(page.get_by_text("No recorded links for this root.")).to_be_visible()
    requests[0].fulfill(
        json={
            "relation": "file_edit",
            "text": "Abandoned response",
            "selector": {
                "document_id": "codex:one",
                "message": 0,
                "tool": 0,
                "field": "tool_result",
                "snapshot": "a" * 64,
            },
        }
    )
    expect(page.get_by_text("Abandoned response")).to_have_count(0)
    expect(page.get_by_role("link", name="Open supporting field")).to_have_count(0)


@pytest.mark.parametrize(
    ("selector", "text", "placeholder"),
    [
        ("&tool=0&field=tool_request", "Dialogue", "No request recorded on this occurrence."),
        ("&field=text", "", "Recorded result"),
    ],
)
def test_guarded_session_link_rejects_missing_or_empty_field(explorer, selector, text, placeholder):
    from playwright.sync_api import expect

    page, access = explorer
    record = _page(0, text, tools=[{"name": "exec", "result": "Recorded result"}])
    access.get_neighborhood_conversation.return_value = record
    access.get_conversation.return_value = record
    source = page.url + "#view=session&project=orchard&document=codex%3Aone&message=0"
    page.goto(source + selector + "&snapshot=" + "a" * 64)

    expect(page.get_by_text("Cited evidence is unavailable.")).to_be_visible(timeout=1500)
    expect(page.locator("#messages")).to_be_empty()

    page.goto(source + selector)
    expect(page.locator(".cited:focus")).to_be_visible()
    expect(page.get_by_text(placeholder, exact=True)).to_be_visible()


def test_approved_playbook_versions_open_guarded_examples(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    access.list_project_playbooks.return_value = {
        "items": [
            {"id": "release", "title": "Release", "version": 2},
            {"id": "docs-release", "title": "Release", "version": 1},
        ],
        "next_after_id": None,
    }

    def version(project, id, version):
        return {
            "project": project,
            "id": id,
            "title": "Release",
            "version": version or 2,
            "latest_version": 2,
            "steps": [MARKUP if version is None else "First release"],
            "examples": [
                {
                    "document_id": "codex:one",
                    "project": project,
                    "source_timestamp": "2026-01-01T00:00:00Z",
                    "snapshot": "a" * 64,
                }
            ],
        }

    access.get_project_playbook.side_effect = version
    access.get_neighborhood_conversation.side_effect = [
        _page(0, "Example transcript", next_offset=50),
        AccessError("not_found"),
    ]
    page.get_by_label("Project slug").fill("orchard")
    page.get_by_role("button", name="Playbooks", exact=True).click()
    expect(
        page.get_by_role("button", name="Release · docs-release · v1", exact=True)
    ).to_be_visible()
    page.get_by_role("button", name="Release · release · v2", exact=True).click()
    expect(page.get_by_text(MARKUP, exact=True)).to_be_visible()
    assert page.locator("#playbooks-detail img").count() == 0
    page.get_by_role("button", name="Older version").click()
    expect(page.get_by_text("First release")).to_be_visible()
    page.get_by_role("button", name="Open example codex:one").click()
    expect(page.get_by_text("Example transcript")).to_be_visible()
    page.get_by_role("button", name="Next messages").click()
    expect(page.get_by_text("Cited evidence is unavailable.")).to_be_visible()
    assert [
        call.kwargs["snapshot"] for call in access.get_neighborhood_conversation.call_args_list
    ] == ["a" * 64] * 2
    page.get_by_label("Project slug").fill("different")
    expect(page.locator("#playbooks-panel")).to_be_hidden()


def test_catalog_paging_discards_an_in_flight_example(explorer):
    from playwright.sync_api import expect

    page, access = explorer
    started, release = Event(), Event()

    def example(**arguments):
        started.set()
        release.wait(10)
        return _page(0, "Superseded transcript")

    access.list_project_playbooks.side_effect = [
        {"items": [{"id": "one", "title": "First", "version": 1}], "next_after_id": "one"},
        {"items": [{"id": "two", "title": "Second", "version": 1}], "next_after_id": None},
    ]
    access.get_project_playbook.return_value = {
        "title": "First",
        "version": 1,
        "latest_version": 1,
        "steps": ["Read"],
        "examples": [
            {
                "document_id": "codex:one",
                "source_timestamp": "2026-01-01T00:00:00Z",
                "snapshot": "a" * 64,
            }
        ],
    }
    access.get_neighborhood_conversation.side_effect = example

    page.get_by_label("Project slug").fill("orchard")
    page.get_by_role("button", name="Playbooks", exact=True).click()
    page.get_by_role("button", name="First · one · v1", exact=True).click()
    page.get_by_role("button", name="Open example codex:one").click()
    try:
        assert started.wait(5)
        page.get_by_role("button", name="More playbooks").click()
        expect(page.get_by_role("button", name="Second · two · v1", exact=True)).to_be_visible()
        expect(page.locator("#evidence")).to_be_hidden()
    finally:
        release.set()
