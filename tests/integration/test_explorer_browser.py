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
def explorer():
    browser_channel = os.environ.get("ENGINEERING_MEMORY_BROWSER")
    if not browser_channel:
        pytest.skip("set ENGINEERING_MEMORY_BROWSER to chromium or msedge")
    from playwright.sync_api import sync_playwright

    from engineering_memory.api.explorer import create_explorer_app

    access = Mock(spec=MemoryAccess)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        authority = f"127.0.0.1:{listener.getsockname()[1]}"
        app = create_explorer_app(access, token=TOKEN, authority=authority)
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
