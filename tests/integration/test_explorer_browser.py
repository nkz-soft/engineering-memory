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
